"""Slice 1A: the confirmation gate. Invariants I1-I10 of the plan spec."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from queryagent.connectors.base import QueryResult
from queryagent.metrics.base import Metric, MetricVariant
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.errors import (
    ConfirmationRequired,
    MappingNotFound,
    PermissionDenied,
    StaleVersion,
    WorkflowStateError,
)
from queryagent.workflow.models import ActorContext, DraftStatus, Rule, RuleSource, RunStatus
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

ALICE = ActorContext(subject_id="alice", workspace_id="ops")
MALLORY = ActorContext(subject_id="mallory", workspace_id="ops")

NEW_USERS = Metric(
    name="new_users",
    display_name="新增用户",
    aliases=("新用户",),
    definition="按 users.created_at 的日期计数（注册口径）；不含 channel='internal_test'。",
    caution="运营口径按 users.first_order_at 计数，两种口径差异很大。",
    tables=("users",),
    variants=(
        MetricVariant("registered", "注册口径", "按 users.created_at 归属日期"),
        MetricVariant("first_order", "首单口径", "按 users.first_order_at 归属日期"),
    ),
)

GMV = Metric(
    name="gmv",
    display_name="成交额",
    definition="status='paid' 订单的 amount 求和。",
    tables=("orders",),
)

TEMPLATES = {
    ("new_users", "registered"): "SELECT COUNT(*) AS n FROM users WHERE channel <> 'internal_test'",
    ("new_users", "first_order"): "SELECT COUNT(*) AS n FROM users "
    "WHERE first_order_at IS NOT NULL AND channel <> 'internal_test'",
}


class StubMetricStore:
    def __init__(self, metrics: tuple[Metric, ...]) -> None:
        self._metrics = metrics

    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        return [m for m in self._metrics if m.display_name and m.display_name in question][:top_k]

    def get(self, name: str) -> Metric | None:
        return next((m for m in self._metrics if m.name == name), None)


class CountingExecutor:
    """Records every business query. The count is the point of most of these tests."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def run(self, sql: str) -> QueryResult:
        self.executed.append(sql)
        return QueryResult(columns=("n",), rows=((42,),), elapsed_ms=1, truncated=False)


@pytest.fixture
def parts(tmp_path: Path) -> tuple[QueryWorkflow, CountingExecutor]:
    executor = CountingExecutor()
    workflow = QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(StubMetricStore((NEW_USERS, GMV))),
        compiler=TemplateCompiler(TEMPLATES),
        executor=executor.run,
        clock=lambda: datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    return workflow, executor


def _pick_registered(workflow: QueryWorkflow, draft_id: str) -> object:
    draft = workflow.get_draft(ALICE, draft_id)
    return workflow.amend(
        ALICE,
        draft_id,
        expected_version=draft.version,
        rules=(Rule("variant", "registered", RuleSource.USER, note="注册口径"),),
    )


# --------------------------------------------------------------- I1, I2, I3


def test_an_unambiguous_question_still_produces_a_draft_not_an_answer(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I2/T01: clarity is not authorisation. No SQL runs during prepare."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "成交额是多少？", request_id="r1")
    assert draft.status is DraftStatus.AWAITING_CONFIRMATION
    assert executor.executed == []


def test_execution_without_a_confirmation_is_refused_and_runs_no_sql(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I1/T01: the central invariant of this slice."""
    workflow, executor = parts
    workflow.prepare(ALICE, "成交额是多少？", request_id="r1")
    with pytest.raises(ConfirmationRequired):
        workflow.execute(ALICE, "made-up-confirmation", idempotency_key="k1")
    assert executor.executed == []


def test_a_caller_claimed_confirmation_flag_is_not_a_confirmation(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I3/T09: only ``confirm()`` mints a confirmation; there is no other door.

    A model that emits ``{"confirmed": true, "subject_id": "alice"}`` reaches
    no API that would accept it — the signature below is the whole surface.
    """
    workflow, executor = parts
    with pytest.raises(TypeError):
        workflow.execute(ALICE, "c1", idempotency_key="k1", confirmed=True)  # type: ignore[call-arg]
    assert executor.executed == []


# ------------------------------------------------------------- draft content


def test_a_metric_with_competing_readings_starts_incomplete(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """D02/T03: both readings stay visible and neither is picked for the user."""
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    assert draft.status is DraftStatus.NEEDS_INPUT
    assert "variant" in draft.definition.missing
    assert {c.key for c in draft.definition.candidates} == {"registered", "first_order"}


def test_confirming_an_incomplete_draft_is_refused(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    with pytest.raises(WorkflowStateError):
        workflow.confirm(
            ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )


def test_a_user_choice_is_labelled_as_the_users_not_the_documents(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """D07: 本次约定 must not be rendered as 文档依据."""
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(workflow, draft.draft_id)
    rule = amended.definition.rule("variant")  # type: ignore[union-attr]
    assert rule is not None and rule.is_user_supplied
    assert amended.status is DraftStatus.AWAITING_CONFIRMATION  # type: ignore[union-attr]


# ------------------------------------------------------------- I4, I5, I6


def test_amending_after_confirmation_invalidates_that_confirmation(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I4/T10: what the user approved is no longer what would run."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(workflow, draft.draft_id)
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,  # type: ignore[union-attr]
        definition_hash=amended.definition_hash,  # type: ignore[union-attr]
    )
    workflow.amend(
        ALICE,
        draft.draft_id,
        expected_version=amended.version,  # type: ignore[union-attr]
        rules=(Rule("variant", "first_order", RuleSource.USER),),
    )
    with pytest.raises(ConfirmationRequired):
        workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert executor.executed == []


def test_confirming_a_stale_version_is_refused(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I5: the user confirmed a screen that has since been superseded."""
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(workflow, draft.draft_id)
    with pytest.raises(StaleVersion):
        workflow.confirm(
            ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )
    assert amended.version == draft.version + 1  # type: ignore[union-attr]


def test_concurrent_amend_loses_loudly(parts: tuple[QueryWorkflow, CountingExecutor]) -> None:
    """I6/T12: two tabs editing the same draft."""
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    _pick_registered(workflow, draft.draft_id)
    with pytest.raises(StaleVersion):
        workflow.amend(
            ALICE,
            draft.draft_id,
            expected_version=draft.version,
            rules=(Rule("variant", "first_order", RuleSource.USER),),
        )


# ------------------------------------------------------------------ I7, I8


def test_a_repeated_request_returns_the_first_run_without_re_executing(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I7/T13: a double-clicked confirm button must not double-query."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(workflow, draft.draft_id)
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,  # type: ignore[union-attr]
        definition_hash=amended.definition_hash,  # type: ignore[union-attr]
    )
    first = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    second = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert first.run_id == second.run_id
    assert len(executor.executed) == 1


def test_another_subject_cannot_use_someone_elses_confirmation(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I8/T06."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(workflow, draft.draft_id)
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,  # type: ignore[union-attr]
        definition_hash=amended.definition_hash,  # type: ignore[union-attr]
    )
    with pytest.raises(PermissionDenied):
        workflow.execute(MALLORY, confirmation.confirmation_id, idempotency_key="k2")
    with pytest.raises(PermissionDenied):
        workflow.get_draft(MALLORY, draft.draft_id)
    assert executor.executed == []


# ---------------------------------------------------------------- I9, I10


def test_a_confirmed_draft_survives_a_restart(tmp_path: Path) -> None:
    """I9/T27: confirm in one process, execute in the next."""
    db = tmp_path / "wf.db"

    def build(executor: CountingExecutor) -> QueryWorkflow:
        return QueryWorkflow(
            store=SqliteWorkflowStore(db),
            builder=MetricDraftBuilder(StubMetricStore((NEW_USERS, GMV))),
            compiler=TemplateCompiler(TEMPLATES),
            executor=executor.run,
            clock=lambda: datetime(2026, 9, 9, tzinfo=timezone.utc),
        )

    first = build(CountingExecutor())
    draft = first.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(first, draft.draft_id)
    confirmation = first.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,  # type: ignore[union-attr]
        definition_hash=amended.definition_hash,  # type: ignore[union-attr]
    )

    executor = CountingExecutor()
    run = build(executor).execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert run.status is RunStatus.SUCCEEDED
    assert run.rows == ((42,),)


def test_an_unmapped_definition_is_refused_rather_than_guessed(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """I10/T14: 成交额 has no maintainer template; nobody invents one."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "成交额是多少？", request_id="r1")
    confirmation = workflow.confirm(
        ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    with pytest.raises(MappingNotFound):
        workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert executor.executed == []


def test_the_executed_sql_matches_the_confirmed_variant(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """The point of the whole chain: the number comes from the confirmed 口径."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = workflow.amend(
        ALICE,
        draft.draft_id,
        expected_version=draft.version,
        rules=(Rule("variant", "first_order", RuleSource.USER),),
    )
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,
        definition_hash=amended.definition_hash,
    )
    run = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert "first_order_at IS NOT NULL" in run.sql
    assert executor.executed == [run.sql]


def test_no_question_match_yields_no_draft_rather_than_a_guess(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """T25: no applicable definition is a fact to report, not a gap to fill."""
    workflow, _ = parts
    with pytest.raises(MappingNotFound):
        workflow.prepare(ALICE, "机房温度多少？", request_id="r1")
