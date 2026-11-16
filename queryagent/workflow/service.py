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
import functools
import inspect
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol, TypeVar, cast

from queryagent.budget import Budget, BudgetExceeded, Lease, Unmetered, metered
from queryagent.connectors.base import QueryResult
from queryagent.knowledge.models import EvidenceRef, RefStatus
from queryagent.knowledge.provider import RetrievalScope, scope_of
from queryagent.workflow import flowtrace
from queryagent.workflow.compiler import CompiledQuery, FreshnessTarget, TemplateCompiler
from queryagent.workflow.coverage import confirmed_period, latest_date
from queryagent.workflow.errors import (
    ConfirmationRequired,
    NotFound,
    PermissionDenied,
    StaleVersion,
    WorkflowError,
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
    DraftProgress,
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


_Method = TypeVar("_Method", bound=Callable[..., Any])


def _watched(step: str) -> Callable[[_Method], _Method]:
    """Trace a refusal from the method, then let it through unchanged (ADR-016).

    The method's second argument names what it acts on: a draft id, or for
    ``execute`` a confirmation id. Every door calls these methods, so every
    door's refusals are traced the same way — and a refusal traced by an
    inner call is not traced again by the one that made it.
    """

    def wrap(method: _Method) -> _Method:
        @functools.wraps(method)
        def inner(
            self: QueryWorkflow, actor: ActorContext, target: str, *args: Any, **kwargs: Any
        ) -> Any:
            try:
                return method(self, actor, target, *args, **kwargs)
            except (WorkflowError, BudgetExceeded) as exc:
                self._trace_refusal(actor, target, step, exc)
                raise

        return cast(_Method, inner)

    return wrap


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
        run_deadline_s: float | None = None,
        emit: flowtrace.Emit | None = None,
    ) -> None:
        self._store = store
        self._builder = builder
        self._builder_takes_actor = _takes_actor(builder)
        self._compiler = compiler
        self._execute_sql = executor
        self._clock = clock
        self._new_id = new_id
        self._ref_checker = ref_checker
        # Fixed here, from the maintainer's config. No method below takes a
        # budget, so nothing a caller passes later can raise it (G2).
        self._budget = budget if budget is not None else Unmetered()
        self._freshness = freshness if freshness is not None else FreshnessPolicy()
        # How long a run may stay 'executing' before no process can still be
        # running it. None: never presumed dead (the behaviour before 1.0.2).
        self._run_deadline_s = run_deadline_s
        # Where the steps of each draft are reported (ADR-016). Decisions are
        # made in this class, so they are traced from this class: no door
        # writes a trace of its own, and so none can tell it differently.
        self._emit_event = emit if emit is not None else flowtrace.silent

    # ------------------------------------------------------------- prepare

    def prepare(self, actor: ActorContext, question: str, *, request_id: str) -> DefinitionDraft:
        """Build and persist a draft 口径. Runs no business SQL.

        A draft is produced even when the question looks unambiguous: the
        confirmation screen is the trust boundary, not a fallback for hard
        questions (D05, T01).
        """
        draft_id = self._new_id()
        # A builder does not know which draft it builds for; what it reports
        # is collected here and traced under this draft, in the order it
        # happened, whether or not a draft comes of it.
        notes: list[tuple[str, dict[str, Any]]] = []
        try:
            with flowtrace.binding(lambda kind, detail: notes.append((kind, dict(detail)))):
                definition = self._build_definition(actor, question)
        except Exception as exc:
            for kind, detail in notes:
                self._trace(actor, draft_id, kind, **detail)
            if isinstance(exc, WorkflowError):
                self._trace_refusal(actor, draft_id, "prepare", exc)
            raise
        for kind, detail in notes:
            self._trace(actor, draft_id, kind, **detail)
        now = self._clock()
        draft = DefinitionDraft(
            draft_id=draft_id,
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
        cited = _cited(definition)
        if cited:
            # Recorded here, once, rather than by each adapter: a door that
            # forgot to would produce drafts whose citations nobody re-checks.
            self._store.set_evidence(actor.subject_id, draft.draft_id, cited)
        self._trace(
            actor,
            draft.draft_id,
            flowtrace.PREPARED,
            question=question,
            metric=definition.metric,
            version=draft.version,
            rules=[f"{rule.key}（{rule.source.value}）" for rule in definition.rules],
            missing=list(definition.missing),
        )
        return draft

    def _trace(self, actor: ActorContext, draft_id: str, kind: str, **detail: Any) -> None:
        self._emit_event(
            flowtrace.FlowEvent(
                kind=kind,
                draft_id=draft_id,
                at=self._clock().isoformat(),
                subject=actor.subject_id,
                workspace=actor.workspace_id,
                channel=actor.channel.value,
                detail=detail,
            )
        )

    def _trace_refusal(
        self, actor: ActorContext, target: str, step: str, exc: BaseException
    ) -> None:
        """One ``refused`` event per refusal, saying no more than the refusal itself says.

        Filed under the acting identity's own workspace, so a refused reach
        into another workspace's draft leaves nothing in that draft's trace.
        """
        if getattr(exc, "_flow_traced", False):
            return
        exc._flow_traced = True  # type: ignore[attr-defined]
        self._trace(
            actor,
            target,
            flowtrace.REFUSED,
            step=step,
            refusal=type(exc).__name__,
            message=str(exc),
        )

    def _build_definition(self, actor: ActorContext, question: str) -> BusinessDefinition:
        """Ask the builder for a draft, passing the identity when it wants one.

        Evidence-backed builders retrieve under the actor's scope; the
        maintainer-only builder has nothing to scope and takes no actor. One
        call site rather than two branches at every caller. Which kind it is
        was read off the signature when the service was built: catching
        ``TypeError`` here instead would also catch one raised *inside* a
        builder, and answer it by building again with nobody's documents.
        """
        if self._builder_takes_actor:
            return self._builder.build(question, actor)
        return self._builder.build(question)

    def _reap(self) -> int:
        """Fail the runs no process can still be running; how many there were.

        A process killed mid-query records nothing, so its run stayed
        'executing' and its draft 'confirmed' for good, with no way forward.
        Every statement has a timeout, so a run older than the deadline is
        not slow, it is gone. It becomes a failed run like any other: the
        confirmation is spent, and the person may confirm again. Called
        wherever a run's status is about to be read or decided on, so no
        background job is needed and every process sharing the state file
        reaches the same answer.
        """
        if self._run_deadline_s is None:
            return 0
        return self._store.abandon_runs(
            started_before=self._clock() - timedelta(seconds=self._run_deadline_s),
            error=(
                "中断：执行它的进程在记录结果之前结束了"
                f"（超过 {self._run_deadline_s:g} 秒没有结果）"
            ),
        )

    def get_draft(self, actor: ActorContext, draft_id: str) -> DefinitionDraft:
        """Read one draft the actor owns, in the workspace they are acting in."""
        return self._draft_of(actor, draft_id)

    def _draft_of(self, actor: ActorContext, draft_id: str) -> DefinitionDraft:
        """The draft, if it is this subject's *and* was prepared in this workspace.

        Every method that takes a draft id reads it through here. A sheet's
        rule values come from its workspace's documents, so the same person
        acting in another workspace is, for this draft, somebody else (P10).
        Found in review: the confirmation page checked this and the MCP door
        did not. Checked once here, no door can forget it. The refusal is the
        one a stranger gets, so it does not say the draft exists elsewhere.
        """
        draft = self._store.get_draft(actor.subject_id, draft_id)
        if draft.workspace_id != actor.workspace_id:
            raise PermissionDenied("not permitted")
        return draft

    def pending_drafts(self, actor: ActorContext) -> tuple[DefinitionDraft, ...]:
        """The actor's drafts in their workspace still waiting on them, newest first (T45)."""
        self._reap()
        return self._store.pending_drafts(actor.subject_id, actor.workspace_id)

    def find_draft(self, actor: ActorContext, prefix: str) -> DefinitionDraft:
        """The actor's draft whose id starts with ``prefix``; the sheet shows eight characters.

        Looked up across the person's workspaces, so the terminal can say
        which ``--workspace`` a draft belongs to. Acting on it still goes
        through the methods that check the workspace.
        """
        ids = self._store.draft_ids_starting(actor.subject_id, prefix)
        if not ids:
            raise NotFound(f"no such draft: {prefix}")
        if len(ids) > 1:
            raise WorkflowStateError(f"草案号 {prefix} 对应 {len(ids)} 份草案；请多写几位")
        return self._store.get_draft(actor.subject_id, ids[0])

    def get_run(self, actor: ActorContext, run_id: str) -> QueryRun:
        """Read one run the actor owns, of a draft in their workspace."""
        self._reap()
        run = self._store.get_run(actor.subject_id, run_id)
        self._draft_of(actor, run.draft_id)
        return run

    def get_run_by_key(self, actor: ActorContext, idempotency_key: str) -> QueryRun | None:
        """The run holding this idempotency key, if any."""
        self._reap()
        run = self._store.get_run_by_key(actor.subject_id, idempotency_key)
        if run is not None:
            self._draft_of(actor, run.draft_id)
        return run

    def attach_evidence(self, actor: ActorContext, draft_id: str, refs: tuple[str, ...]) -> None:
        """Record the citations this draft rests on, for later re-checking."""
        self._draft_of(actor, draft_id)
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
        draft = self._draft_of(actor, draft_id)
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

    @_watched("amend")
    def amend(
        self,
        actor: ActorContext,
        draft_id: str,
        *,
        expected_version: int,
        rules: tuple[Rule, ...],
    ) -> DefinitionDraft:
        """Apply the caller's own rules and bump the version.

        Every amendment produces a new version and therefore a new content
        hash, which is what makes an earlier confirmation stop matching
        (§9.2 invariants 4-5). ``expected_version`` makes a second editor
        lose loudly instead of overwriting what the first one confirmed.

        An amendment is, by definition, what this caller supplied this time:
        ``USER``-sourced from a person, ``AGENT``-sourced from an agent over
        MCP (ADR-013). The service enforces that rather than trusting callers
        to: ``Rule.__post_init__`` only checks that a DOC rule's
        ``evidence_ref`` is non-empty, so any string would buy a 「文档依据」
        label on the confirmation sheet — the one distinction this product
        exists to keep honest (D07). And an agent's guess must not read as
        what the person agreed.
        """
        authoring = actor.authoring_source
        forged = [rule for rule in rules if rule.source is not authoring]
        if forged:
            keys = ", ".join(sorted(rule.key for rule in forged))
            if authoring is RuleSource.AGENT:
                raise WorkflowStateError(
                    f"Agent 补充的规则只能标为「Agent 代填」，不能自称文档依据、本次约定或"
                    f"系统映射：{keys}"
                )
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
        current = self._draft_of(actor, draft_id)
        # A caller's rule may carry a citation only by adopting wording the
        # sheet already shows with that citation. Any other string would put
        # a source on the sheet that retrieval never returned for this
        # identity and that is never re-checked (D07). The doors build rules
        # through ``answers``, which cannot do this; a caller of this method
        # could.
        known = set(_cited(current.definition))
        uncited = sorted(
            rule.key for rule in rules if rule.evidence_ref and rule.evidence_ref not in known
        )
        if uncited:
            raise WorkflowStateError(
                f"补充的规则只能引用这份确认单上已有的出处：{', '.join(uncited)}"
            )
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
        self._trace(
            actor,
            draft_id,
            flowtrace.AMENDED,
            version=updated.version,
            rules=[f"{rule.key}={rule.value}（{rule.source.value}）" for rule in rules],
            missing=list(definition.missing),
        )
        return updated

    def amend_from(
        self,
        actor: ActorContext,
        draft_id: str,
        *,
        expected_version: int,
        read: Callable[[DefinitionDraft], tuple[Rule, ...]],
    ) -> DefinitionDraft:
        """Amend with whatever ``read`` makes of an answer, given the stored draft.

        For the doors that take a typed or structured answer (the page, MCP).
        Reading it can refuse — a reading nobody declared, a period that
        cannot be parsed — and that refusal used to happen in the door,
        before the service was called, so it was the one kind the trace
        never saw (found in the 1.1 read-through). Read here, it is traced
        like any other.

        Raises:
            ValueError: The answer fits nothing on the draft; from ``read``.
            WorkflowError: As ``amend``.
        """
        try:
            rules = read(self._draft_of(actor, draft_id))
        except (ValueError, WorkflowError) as exc:
            self._trace_refusal(actor, draft_id, "amend", exc)
            raise
        return self.amend(actor, draft_id, expected_version=expected_version, rules=rules)

    # ------------------------------------------------------------- confirm

    @_watched("confirm")
    def confirm(
        self, actor: ActorContext, draft_id: str, *, version: int, definition_hash: str
    ) -> Confirmation:
        """Record that this subject approved this exact draft version.

        Both ``version`` and ``definition_hash`` must match what the store
        holds: the caller is asserting *which screen they were looking at*,
        and a mismatch means they were looking at a different one.

        Only a person confirms. The MCP adapter offers no way to call this,
        and the check here holds even for one that tried (H1, ADR-013).
        """
        if not actor.channel.is_human:
            raise PermissionDenied(
                "确认只能由人在终端（queryagent confirm）或本地确认页（queryagent web）完成；"
                "Agent 通道不能确认"
            )
        draft = self._draft_of(actor, draft_id)
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
            channel=actor.channel,
        )
        self._store.save_confirmation(confirmation)
        self._trace(
            actor,
            draft_id,
            flowtrace.CONFIRMED,
            version=draft.version,
            definition_hash=draft.definition_hash[:16],
        )
        return confirmation

    def human_confirmation(self, actor: ActorContext, draft_id: str) -> Confirmation | None:
        """The confirmation a person gave the draft's current version, if any."""
        draft = self._draft_of(actor, draft_id)
        return self._store.human_confirmation(
            actor.subject_id, draft_id, draft.version, draft.definition_hash
        )

    def last_run(self, actor: ActorContext, draft_id: str) -> QueryRun | None:
        """The newest run of the draft's current, confirmed version, if any."""
        confirmation = self.human_confirmation(actor, draft_id)
        if confirmation is None:
            return None
        self._reap()
        return self._store.latest_run_of(actor.subject_id, confirmation.confirmation_id)

    def progress(self, actor: ActorContext, draft_id: str) -> DraftProgress:
        """Where the draft stands, for a caller asking after it (T44)."""
        draft = self._draft_of(actor, draft_id)
        if draft.status is DraftStatus.EXPIRED:
            return DraftProgress.EXPIRED
        if self.human_confirmation(actor, draft_id) is None:
            if draft.status is DraftStatus.NEEDS_INPUT:
                return DraftProgress.NEEDS_INPUT
            return DraftProgress.AWAITING_CONFIRMATION
        run = self.last_run(actor, draft_id)
        if run is not None and run.status is RunStatus.SUCCEEDED:
            return DraftProgress.EXECUTED
        if run is not None and run.status is RunStatus.FAILED:
            return DraftProgress.FAILED
        return DraftProgress.CONFIRMED

    @_watched("execute")
    def execute_confirmed(self, actor: ActorContext, draft_id: str) -> QueryRun:
        """Run the draft's current version once a person has confirmed it (T44, H3).

        The door for callers that cannot confirm — an agent over MCP. It names
        a draft, not a confirmation: the service looks up one a person gave
        this exact version and hash, and without one nothing runs. One
        confirmation authorises one run: the confirmation is the idempotency
        key, so asking again answers from the stored run instead of querying
        twice, and running again takes a person confirming again.
        """
        draft = self._draft_of(actor, draft_id)
        if draft.status is DraftStatus.EXPIRED:
            raise ConfirmationRequired(f"draft {draft_id} has expired; prepare it again")
        confirmation = self._store.human_confirmation(
            actor.subject_id, draft_id, draft.version, draft.definition_hash
        )
        if confirmation is None:
            raise ConfirmationRequired(
                f"草案 #{draft_id[:8]} 的当前版本（v{draft.version}）还没有人确认。请用户在本地"
                f"确认页（queryagent web）或终端（queryagent confirm {draft_id[:8]}）确认后再"
                "执行；确认前不会执行任何查询。"
            )
        return self.execute(
            actor,
            confirmation.confirmation_id,
            idempotency_key=f"confirmation:{confirmation.confirmation_id}",
        )

    # ------------------------------------------------------------- execute

    def execute(
        self, actor: ActorContext, confirmation_id: str, *, idempotency_key: str
    ) -> QueryRun:
        """Run the confirmed 口径 once; see ``_execute`` for the order of checks.

        A refusal is traced under the draft the confirmation names, when
        there is one this caller may see.
        """
        try:
            return self._execute(actor, confirmation_id, idempotency_key=idempotency_key)
        except (WorkflowError, BudgetExceeded) as exc:
            self._trace_refusal(actor, self._draft_behind(actor, confirmation_id), "execute", exc)
            raise

    def _draft_behind(self, actor: ActorContext, confirmation_id: str) -> str:
        """The draft a confirmation names, for filing a trace.

        A confirmation that does not exist, or is somebody else's, names no
        draft this caller may hear about: the refusal is filed under
        ``unconfirmed`` in the caller's own workspace.
        """
        try:
            return self._store.get_confirmation(actor.subject_id, confirmation_id).draft_id
        except WorkflowError:
            return "unconfirmed"

    def _execute(
        self, actor: ActorContext, confirmation_id: str, *, idempotency_key: str
    ) -> QueryRun:
        """Run the confirmed 口径 once.

        A confirmation is spent by its first run. Asking again — with the same
        key or another — returns that run and queries nothing; running again
        takes a person confirming again.

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
        draft = self._draft_of(actor, confirmation.draft_id)
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
            started_at=self._clock().isoformat(),
        )
        self._reap()
        # A replay is the same request, not a new one: it answers from the
        # stored run whatever today's budget says (T13). Found in testing —
        # admitting first refused replays once the allowance ran low.
        earlier = self._store.get_run_by_key(actor.subject_id, idempotency_key)
        if earlier is not None:
            self._trace_replay(actor, earlier, "同一个幂等键已有运行")
            return earlier
        # One confirmation authorises one run, whichever door asks and under
        # whatever key (ADR-013). Found in review: a run made under one key
        # could be made again through ``execute_confirmed``, which uses another.
        spent = self._store.latest_run_of(actor.subject_id, confirmation.confirmation_id)
        if spent is not None:
            self._trace_replay(actor, spent, "这次确认已经有过一次运行")
            return spent
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
                self._trace_replay(actor, existing, "另一个请求先占了位")
                return existing  # T13: the same request, not a second query
            self._trace(
                actor,
                run.draft_id,
                flowtrace.ADMITTED,
                statements=2 if probe else 1,
                idempotency_key=idempotency_key,
            )
            try:
                finished = self._run(run, query, probe, lease)
            except Exception as exc:
                self._trace(
                    actor,
                    run.draft_id,
                    flowtrace.EXECUTED,
                    status=RunStatus.FAILED.value,
                    error=f"{type(exc).__name__}: {exc}",
                    sql=run.sql,
                    params=list(run.params),
                )
                raise
            self._trace(
                actor,
                run.draft_id,
                flowtrace.EXECUTED,
                status=finished.status.value,
                sql=finished.sql,
                params=list(finished.params),
                row_count=len(finished.rows),
                columns=list(finished.columns),
                data_through=finished.data_through,
            )
            return finished

    def _trace_replay(self, actor: ActorContext, run: QueryRun, why: str) -> None:
        self._trace(
            actor,
            run.draft_id,
            flowtrace.ADMITTED,
            replay=why,
            answered_with=f"运行 {run.run_id[:8]}（{run.status.value}），没有执行新的语句",
        )

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
            self._store.finish_run(failed)  # a no-op if the run was failed as abandoned
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
        if not self._store.finish_run(finished):
            # Finished after its deadline: the run was already failed as
            # abandoned and its confirmation is spent. What is stored is the
            # answer, not a result nobody is waiting for any more.
            return self._store.get_run(run.subject_id, run.run_id)
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


def _takes_actor(builder: DraftBuilder) -> bool:
    """Whether ``builder.build`` accepts the identity after the question."""
    try:
        parameters = inspect.signature(builder.build).parameters.values()
    except (TypeError, ValueError):  # no readable signature: assume the full protocol
        return True
    positional = [
        p for p in parameters if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional) >= 2 or any(p.kind is p.VAR_POSITIONAL for p in parameters)


def _cited(definition: BusinessDefinition) -> tuple[str, ...]:
    """Every citation on the sheet: the rules' and the competing readings'."""
    refs = [rule.evidence_ref for rule in definition.rules] + [
        candidate.evidence_ref for candidate in definition.candidates
    ]
    return tuple(dict.fromkeys(ref for ref in refs if ref))


def _latest_in(result: QueryResult) -> date | None:
    """The date in a ``MAX(time_column)`` result, or None when there is none."""
    first = result.rows[0][0] if result.rows and result.rows[0] else None
    return latest_date(first)
