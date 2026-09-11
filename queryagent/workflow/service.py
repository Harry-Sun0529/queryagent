"""The trusted workflow: prepare → amend → confirm → execute.

Everything that decides *whether* a business query runs lives here, once.
CLI, Web and MCP are protocol adapters over this object; none of them gets
its own copy of the rules, because a check that exists in two places is a
check that will eventually exist in one (D26/T26).

The three properties this class is built to hold:

1. ``execute`` reads the draft and the confirmation back out of the store and
   re-checks them. Anything the caller hands in is a claim.
2. A confirmation is bound to a draft *version* and a *content hash*. Change
   the meaning and the confirmation no longer matches the draft it names.
3. There is no argument, anywhere in this API, by which a caller asserts that
   something was confirmed. ``confirm()`` is the only way one comes to exist,
   and it takes a trusted :class:`ActorContext` (D06, D11, T09).
"""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from queryagent.budget import Budget, Lease, Unmetered, metered
from queryagent.connectors.base import QueryResult
from queryagent.knowledge.models import EvidenceRef, RefStatus
from queryagent.knowledge.provider import RetrievalScope, scope_of
from queryagent.workflow.compiler import CompiledQuery, FreshnessTarget, TemplateCompiler
from queryagent.workflow.coverage import confirmed_period, latest_date
from queryagent.workflow.errors import (
    ConfirmationRequired,
    NotFound,
    StaleVersion,
    WorkflowStateError,
)
from queryagent.workflow.freshness import (
    OFF,
    PROBE,
    PROBE_FAILED,
    FreshnessPolicy,
    describe_declared,
    describe_probed,
    expected_latest,
)
from queryagent.workflow.models import (
    VARIANT_RULE_KEY,
    ActorContext,
    BusinessDefinition,
    Confirmation,
    DefinitionDraft,
    DraftStatus,
    QueryRun,
    Rule,
    RuleSource,
    RunStatus,
)
from queryagent.workflow.periods import Period
from queryagent.workflow.store import SqliteWorkflowStore


class DraftBuilder(Protocol):
    """Turns a question into a 口径 to confirm.

    Two implementations: maintainer metrics alone (slice 1A) and those plus
    authorised document evidence (1B). The seam is a Protocol so the service
    does not have to know which it holds — and so a third one can be a
    third file rather than a branch in here.
    """

    def build(self, question: str, actor: ActorContext | None = ...) -> BusinessDefinition:
        ...


class RefChecker(Protocol):
    """Re-checks stored citations. Satisfied by ``LocalKnowledgeProvider``."""

    def check_refs(
        self, scope: RetrievalScope, refs: tuple[EvidenceRef, ...]
    ) -> tuple[object, ...]: ...


Executor = Callable[[CompiledQuery], QueryResult]
Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class QueryWorkflow:
    """Application service owning request state and the confirmation gate."""

    def __init__(
        self,
        *,
        store: SqliteWorkflowStore,
        builder: DraftBuilder,
        compiler: TemplateCompiler,
        executor: Executor,
        clock: Clock = _now,
        new_id: IdFactory = _uuid,
        ref_checker: RefChecker | None = None,
        budget: Budget | None = None,
        freshness: FreshnessPolicy | None = None,
    ) -> None:
        self._store = store
        self._builder = builder
        self._compiler = compiler
        self._execute_sql = executor
        self._clock = clock
        self._new_id = new_id
        self._ref_checker = ref_checker
        # Fixed here, from the maintainer's config. No method below takes a
        # budget, so nothing a caller passes later can raise it (G2).
        self._budget = budget if budget is not None else Unmetered()
        self._freshness = freshness if freshness is not None else FreshnessPolicy()

    # ------------------------------------------------------------- prepare

    def prepare(self, actor: ActorContext, question: str, *, request_id: str) -> DefinitionDraft:
        """Build and persist a draft 口径. Runs no business SQL.

        A draft is produced even when the question looks unambiguous: the
        confirmation screen is the trust boundary, not a fallback for hard
        questions (D05, T01).
        """
        definition = self._build_definition(actor, question)
        now = self._clock()
        draft = DefinitionDraft(
            draft_id=self._new_id(),
            request_id=request_id,
            subject_id=actor.subject_id,
            workspace_id=actor.workspace_id,
            question=question,
            version=1,
            status=(
                DraftStatus.AWAITING_CONFIRMATION
                if definition.is_complete
                else DraftStatus.NEEDS_INPUT
            ),
            definition=definition,
            created_at=now,
            updated_at=now,
        )
        self._store.create_draft(draft)
        return draft

    def _build_definition(self, actor: ActorContext, question: str) -> BusinessDefinition:
        """Ask the builder for a draft, passing the identity when it wants one.

        Evidence-backed builders retrieve under the actor's scope; the
        maintainer-only builder has nothing to scope and takes no actor. One
        call site rather than two branches at every caller.
        """
        try:
            return self._builder.build(question, actor)
        except TypeError:
            return self._builder.build(question)

    def get_draft(self, actor: ActorContext, draft_id: str) -> DefinitionDraft:
        """Read one draft the actor owns."""
        return self._store.get_draft(actor.subject_id, draft_id)

    def get_run(self, actor: ActorContext, run_id: str) -> QueryRun:
        """Read one run the actor owns."""
        return self._store.get_run(actor.subject_id, run_id)

    def get_run_by_key(self, actor: ActorContext, idempotency_key: str) -> QueryRun | None:
        """The run holding this idempotency key, if any."""
        return self._store.get_run_by_key(actor.subject_id, idempotency_key)

    def attach_evidence(self, actor: ActorContext, draft_id: str, refs: tuple[str, ...]) -> None:
        """Record the citations this draft rests on, for later re-checking."""
        self._store.set_evidence(actor.subject_id, draft_id, refs)

    def _evidence_still_stands(self, actor: ActorContext, draft_id: str) -> None:
        """Re-check every citation, or raise.

        Called before minting a confirmation and again before executing one.
        Access is withdrawn in the gap between those two moments, and only a
        check at each end closes it. A draft with no citations skips this
        entirely, which is what keeps maintainer-only drafts behaving exactly
        as they did in 1A.
        """
        if self._ref_checker is None:
            return
        stored = self._store.evidence_of(actor.subject_id, draft_id)
        if not stored:
            return
        refs = tuple(EvidenceRef.parse(ref) for ref in stored)
        statuses = self._ref_checker.check_refs(scope_of(actor), refs)
        if all(status is RefStatus.OK for status in statuses):
            return
        self._store.expire_draft(actor.subject_id, draft_id)
        # One message for withdrawn and for edited: which of the two it was
        # can itself disclose a document the caller may not know about.
        raise ConfirmationRequired(
            "口径所依据的文档已失效（内容变更、被移除，或访问权限调整）；需要重新生成确认单"
        )

    # ----------------------------------------------------------- freshness

    def freshness_advisory(self, actor: ActorContext, draft_id: str) -> tuple[str, ...]:
        """Notes for the sheet on how far the data reaches, before confirmation (T41).

        Advice, not state: not stored on the draft and not in its hash, so a
        probe's answer changing as data loads never expires a confirmation
        (G10). In the default ``declared`` mode this runs nothing (G8). In
        ``probe`` mode the only statements it may run are the compiler's own
        ``MAX()`` probes, cached and charged to the budget (G9, ADR-010).
        Nothing is said without a period: there is no range to fall short of.
        """
        draft = self._store.get_draft(actor.subject_id, draft_id)
        period = confirmed_period(draft.definition)
        if self._freshness.mode == OFF or period is None:
            return ()
        targets = self._compiler.freshness_targets(draft.definition)
        notes = []
        for target in targets:
            note = self._freshness_note(actor, target, period)
            if note:
                # Before a reading is chosen, each reading's table may reach
                # a different date; say which is which.
                prefix = f"{target.source}.{target.time_column}：" if len(targets) > 1 else ""
                notes.append(prefix + note)
        return tuple(notes)

    def _freshness_note(self, actor: ActorContext, target: FreshnessTarget, period: Period) -> str:
        if self._freshness.mode == PROBE:
            found = self._probe_before_confirmation(actor, target)
            if found is not None:
                latest, probed_at = found
                return describe_probed(period, latest, probed_at, self._freshness.zone)
            if target.lag_days is None:
                return PROBE_FAILED
        if target.lag_days is None:
            return ""
        return describe_declared(period, target.lag_days, self._freshness.today())

    def _probe_before_confirmation(
        self, actor: ActorContext, target: FreshnessTarget
    ) -> tuple[date, datetime] | None:
        """The newest record's date in one table and when it was read, or None.

        Cached per table for ``cache_minutes``; the answer is the same for
        everyone who may query the table. A failure — timeout, error, spent
        budget — costs the note, never the draft.
        """
        policy = self._freshness
        if policy.probe is None:
            return None
        now = self._clock()
        cached = self._store.cached_freshness(target.source, target.time_column)
        if cached is not None and now - cached.probed_at < timedelta(minutes=policy.cache_minutes):
            return date.fromisoformat(cached.latest), cached.probed_at
        try:
            with self._budget.admit(actor.subject_id, queries=1) as lease, metered(lease):
                latest = _latest_in(policy.probe(target.probe))
        except Exception:  # noqa: BLE001 - advice only; see the docstring
            return None
        if latest is None:
            return None
        self._store.cache_freshness(target.source, target.time_column, latest.isoformat(), now)
        return latest, now

    def _expected_through(self, definition: BusinessDefinition) -> str:
        """Where the declared cadence says this reading's data should reach today, or ''."""
        targets = self._compiler.freshness_targets(definition)
        if len(targets) != 1 or targets[0].lag_days is None:
            return ""
        return expected_latest(self._freshness.today(), targets[0].lag_days).isoformat()

    # --------------------------------------------------------------- amend

    def amend(
        self,
        actor: ActorContext,
        draft_id: str,
        *,
        expected_version: int,
        rules: tuple[Rule, ...],
    ) -> DefinitionDraft:
        """Apply the user's own rules and bump the version.

        Every amendment produces a new version and therefore a new content
        hash, which is what makes an earlier confirmation stop matching
        (§9.2 invariants 4-5). ``expected_version`` makes a second editor
        lose loudly instead of overwriting what the first one confirmed.

        An amendment is, by definition, what this user agreed this time, so
        every rule it carries is ``USER``-sourced. The service enforces that
        rather than trusting callers to: ``Rule.__post_init__`` only checks
        that a DOC rule's ``evidence_ref`` is non-empty, so any string would
        buy a 「文档依据」 label on the confirmation sheet — the one
        distinction this product exists to keep honest (D07).
        """
        forged = [rule for rule in rules if rule.source is not RuleSource.USER]
        if forged:
            keys = ", ".join(sorted(rule.key for rule in forged))
            raise WorkflowStateError(
                f"用户补充的规则只能标为「本次约定」，不能自称文档依据或系统映射：{keys}"
            )
        # One amendment is one act of one user. Adopting a handbook's wording
        # that names one reading while choosing another in the same breath
        # is a contradiction, and running either is a guess (F13). Choosing
        # against a handbook in a *separate* amendment stays allowed — it is
        # shown on the sheet as a conflict.
        chosen = next((rule for rule in rules if rule.key == VARIANT_RULE_KEY), None)
        if chosen is not None:
            contradicted = sorted(
                rule.key
                for rule in rules
                if rule.key != VARIANT_RULE_KEY
                and rule.implies
                and chosen.value not in rule.implies
            )
            if contradicted:
                raise WorkflowStateError(
                    f"同一次补充里，采用的文档写法（{', '.join(contradicted)}）对应的口径与"
                    f"选定口径 {chosen.value} 矛盾；请只保留一个"
                )
        current = self._store.get_draft(actor.subject_id, draft_id)
        definition = current.definition.with_rules(rules)
        updated = DefinitionDraft(
            draft_id=current.draft_id,
            request_id=current.request_id,
            subject_id=current.subject_id,
            workspace_id=current.workspace_id,
            question=current.question,
            version=current.version + 1,
            status=(
                DraftStatus.AWAITING_CONFIRMATION
                if definition.is_complete
                else DraftStatus.NEEDS_INPUT
            ),
            definition=definition,
            created_at=current.created_at,
            updated_at=self._clock(),
        )
        self._store.update_draft(actor.subject_id, updated, expected_version=expected_version)
        return updated

    # ------------------------------------------------------------- confirm

    def confirm(
        self, actor: ActorContext, draft_id: str, *, version: int, definition_hash: str
    ) -> Confirmation:
        """Record that this subject approved this exact draft version.

        Both ``version`` and ``definition_hash`` must match what the store
        holds: the caller is asserting *which screen they were looking at*,
        and a mismatch means they were looking at a different one.
        """
        draft = self._store.get_draft(actor.subject_id, draft_id)
        if draft.version != version or draft.definition_hash != definition_hash:
            raise StaleVersion(
                f"draft {draft_id} is at version {draft.version}; "
                "review the current 口径 and confirm again"
            )
        self._evidence_still_stands(actor, draft_id)
        if not draft.definition.is_complete:
            raise WorkflowStateError(
                "cannot confirm a 口径 with undetermined rules: "
                + ", ".join(draft.definition.missing)
            )
        confirmation = Confirmation(
            confirmation_id=self._new_id(),
            draft_id=draft.draft_id,
            draft_version=draft.version,
            definition_hash=draft.definition_hash,
            subject_id=actor.subject_id,
            confirmed_at=self._clock(),
        )
        self._store.save_confirmation(confirmation)
        return confirmation

    # ------------------------------------------------------------- execute

    def execute(
        self, actor: ActorContext, confirmation_id: str, *, idempotency_key: str
    ) -> QueryRun:
        """Run the confirmed 口径 once.

        Order matters: identity, then confirmation validity against current
        stored state, then the budget's admission, then the idempotency
        claim, and only then SQL. A rejection at any earlier step must leave
        the database untouched — and a budget refusal the idempotency key
        unspent, so the same request can run once the budget allows (G3).
        """
        try:
            confirmation = self._store.get_confirmation(actor.subject_id, confirmation_id)
        except NotFound as exc:
            # On the read path "no such object" is the useful answer; on the
            # execute path there is only one question worth answering, and
            # callers should not have to catch two errors to hear "no".
            raise ConfirmationRequired(f"no confirmation to execute: {confirmation_id}") from exc
        draft = self._store.get_draft(actor.subject_id, confirmation.draft_id)
        if (
            draft.version != confirmation.draft_version
            or draft.definition_hash != confirmation.definition_hash
        ):
            raise ConfirmationRequired(
                f"the 口径 changed after confirmation (draft is at version {draft.version}); "
                "confirm the current version before running it"
            )
        if draft.status is DraftStatus.EXPIRED:
            raise ConfirmationRequired(f"draft {draft.draft_id} has expired; prepare it again")
        # Before compiling and before claiming the key: a refusal here must
        # leave the database untouched and the idempotency key unspent.
        self._evidence_still_stands(actor, draft.draft_id)

        # Compiling before claiming the key keeps an unmappable definition
        # from burning the caller's idempotency key on a run that never ran.
        query = self._compiler.compile(draft.definition)
        probe = self._compiler.freshness_probe(draft.definition)

        run = QueryRun(
            run_id=self._new_id(),
            draft_id=draft.draft_id,
            confirmation_id=confirmation.confirmation_id,
            subject_id=actor.subject_id,
            idempotency_key=idempotency_key,
            status=RunStatus.EXECUTING,
            sql=query.sql,
            params=query.params,
            expected_through=self._expected_through(draft.definition),
            mapping_fingerprint=self._compiler.fingerprint(draft.definition),
        )
        # A replay is the same request, not a new one: it answers from the
        # stored run whatever today's budget says (T13). Found in testing —
        # admitting first refused replays once the allowance ran low.
        earlier = self._store.get_run_by_key(actor.subject_id, idempotency_key)
        if earlier is not None:
            return earlier
        # Admitted after every check that needs no database and before the
        # idempotency claim. The probe is reserved with the query: it is a
        # statement too, and a budget that forgot it would be an undercount.
        with self._budget.admit(actor.subject_id, queries=2 if probe else 1) as lease:
            try:
                existing = self._store.claim_run(run)
            except BaseException:
                lease.refund()
                raise
            if existing is not None:
                lease.refund()  # a replay runs nothing, so it costs nothing
                return existing  # T13: the same request, not a second query
            return self._run(run, query, probe, lease)

    def _run(
        self, run: QueryRun, query: CompiledQuery, probe: CompiledQuery | None, lease: Lease
    ) -> QueryRun:
        """Date the data, run the query, and record the outcome on the claimed run."""
        freshness_sql = probe.sql if probe else ""
        data_through = self._date_the_data(probe, lease)
        try:
            with metered(lease):
                result = self._execute_sql(query)
        except Exception as exc:
            failed = dataclasses.replace(
                run,
                status=RunStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                freshness_sql=freshness_sql,
                data_through=data_through,
            )
            self._store.finish_run(failed)
            raise
        # Replaced, not rebuilt field by field: a field added to the claimed
        # run later is carried to the record without anyone remembering to.
        finished = dataclasses.replace(
            run,
            status=RunStatus.SUCCEEDED,
            columns=tuple(result.columns),
            rows=tuple(tuple(row) for row in result.rows),
            truncated=result.truncated,
            freshness_sql=freshness_sql,
            data_through=data_through,
        )
        self._store.finish_run(finished)
        return finished

    def _date_the_data(self, probe: CompiledQuery | None, lease: Lease) -> str:
        """ISO date of the newest record behind this query, or '' if unknown.

        Called only once the confirmation, the evidence, the budget and the
        idempotency claim have all held — the point the query itself runs — so the
        rule that nothing touches the database before confirmation is kept
        (F6). That is also why the sheet cannot warn about a partial month:
        finding out takes a query. A probe that fails costs the note, never
        the number the user confirmed.
        """
        if probe is None:
            return ""
        try:
            with metered(lease):
                result = self._execute_sql(probe)
        except Exception:  # noqa: BLE001 - reported as "unknown" on the result
            return ""
        latest = _latest_in(result)
        return latest.isoformat() if latest else ""


def _latest_in(result: QueryResult) -> date | None:
    """The date in a ``MAX(time_column)`` result, or None when there is none."""
    first = result.rows[0][0] if result.rows and result.rows[0] else None
    return latest_date(first)
