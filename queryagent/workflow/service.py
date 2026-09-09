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

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from queryagent.connectors.base import QueryResult
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.errors import (
    ConfirmationRequired,
    NotFound,
    StaleVersion,
    WorkflowStateError,
)
from queryagent.workflow.models import (
    ActorContext,
    Confirmation,
    DefinitionDraft,
    DraftStatus,
    QueryRun,
    Rule,
    RuleSource,
    RunStatus,
)
from queryagent.workflow.store import SqliteWorkflowStore

Executor = Callable[[str], QueryResult]
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
        builder: MetricDraftBuilder,
        compiler: TemplateCompiler,
        executor: Executor,
        clock: Clock = _now,
        new_id: IdFactory = _uuid,
    ) -> None:
        self._store = store
        self._builder = builder
        self._compiler = compiler
        self._execute_sql = executor
        self._clock = clock
        self._new_id = new_id

    # ------------------------------------------------------------- prepare

    def prepare(self, actor: ActorContext, question: str, *, request_id: str) -> DefinitionDraft:
        """Build and persist a draft 口径. Runs no business SQL.

        A draft is produced even when the question looks unambiguous: the
        confirmation screen is the trust boundary, not a fallback for hard
        questions (D05, T01).
        """
        definition = self._builder.build(question)
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

    def get_draft(self, actor: ActorContext, draft_id: str) -> DefinitionDraft:
        """Read one draft the actor owns."""
        return self._store.get_draft(actor.subject_id, draft_id)

    def get_run(self, actor: ActorContext, run_id: str) -> QueryRun:
        """Read one run the actor owns."""
        return self._store.get_run(actor.subject_id, run_id)

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
        stored state, then the idempotency claim, and only then SQL. A
        rejection at any earlier step must leave the database untouched.
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

        # Compiling before claiming the key keeps an unmappable definition
        # from burning the caller's idempotency key on a run that never ran.
        sql = self._compiler.compile(draft.definition)

        run = QueryRun(
            run_id=self._new_id(),
            draft_id=draft.draft_id,
            confirmation_id=confirmation.confirmation_id,
            subject_id=actor.subject_id,
            idempotency_key=idempotency_key,
            status=RunStatus.EXECUTING,
            sql=sql,
        )
        existing = self._store.claim_run(run)
        if existing is not None:
            return existing  # T13: the same request, not a second query

        try:
            result = self._execute_sql(sql)
        except Exception as exc:
            failed = QueryRun(
                run_id=run.run_id,
                draft_id=run.draft_id,
                confirmation_id=run.confirmation_id,
                subject_id=run.subject_id,
                idempotency_key=run.idempotency_key,
                status=RunStatus.FAILED,
                sql=sql,
                error=f"{type(exc).__name__}: {exc}",
            )
            self._store.finish_run(failed)
            raise
        finished = QueryRun(
            run_id=run.run_id,
            draft_id=run.draft_id,
            confirmation_id=run.confirmation_id,
            subject_id=run.subject_id,
            idempotency_key=run.idempotency_key,
            status=RunStatus.SUCCEEDED,
            sql=sql,
            columns=tuple(result.columns),
            rows=tuple(tuple(row) for row in result.rows),
            truncated=result.truncated,
        )
        self._store.finish_run(finished)
        return finished
