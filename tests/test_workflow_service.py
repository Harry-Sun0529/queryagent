"""Slice 1A: the confirmation gate. Invariants I1-I10 of the plan spec."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from queryagent.connectors.base import QueryResult
from queryagent.metrics.base import Metric, MetricVariant
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import CompiledQuery, TemplateCompiler
from queryagent.workflow.errors import (
    ConfirmationRequired,
    MappingNotFound,
    PermissionDenied,
    StaleVersion,
    WorkflowStateError,
)
from queryagent.workflow.mappings import QueryMapping
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
    ("new_users", "registered"): QueryMapping(
        source="users",
        measure="COUNT(*)",
        label="n",
        time_column="created_at",
        where=("channel <> 'internal_test'",),
    ),
    ("new_users", "first_order"): QueryMapping(
        source="users",
        measure="COUNT(*)",
        label="n",
        time_column="first_order_at",
        where=("first_order_at IS NOT NULL", "channel <> 'internal_test'"),
    ),
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
        self.bound: list[tuple[str, ...]] = []

    def run(self, query: CompiledQuery) -> QueryResult:
        self.executed.append(query.sql)
        self.bound.append(query.params)
        if query.sql.startswith("SELECT MAX("):  # the freshness probe (T37)
            return QueryResult(
                columns=("latest",), rows=(("2026-08-22 10:00:00",),), elapsed_ms=1, truncated=False
            )
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
    # One run's statements — the freshness probe, then the query — and none for the replay.
    assert executor.executed == ["SELECT MAX(created_at) FROM users", first.sql]


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
    assert executor.executed == ["SELECT MAX(first_order_at) FROM users", run.sql]


def test_no_question_match_yields_no_draft_rather_than_a_guess(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """T25: no applicable definition is a fact to report, not a gap to fill."""
    workflow, _ = parts
    with pytest.raises(MappingNotFound):
        workflow.prepare(ALICE, "机房温度多少？", request_id="r1")


# ------------------------------------------------------------------ K14


def test_amend_refuses_rules_that_claim_a_document_said_it(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """K14: a caller must not be able to forge 「文档依据」.

    ``Rule.__post_init__`` only checks that a DOC rule's evidence_ref is
    non-empty — any string passes. Today the CLI happens to hardcode USER,
    but that is caller discipline, and ``amend`` is the API a Web or MCP
    entry point will call. An amendment is by definition what the user
    agreed this time, so the service, not its callers, decides that.
    """
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    with pytest.raises(WorkflowStateError, match="本次约定"):
        workflow.amend(
            ALICE,
            draft.draft_id,
            expected_version=draft.version,
            rules=(Rule("variant", "registered", RuleSource.DOC, evidence_ref="doc:fake#1"),),
        )
    unchanged = workflow.get_draft(ALICE, draft.draft_id)
    assert unchanged.version == draft.version
    assert unchanged.definition_hash == draft.definition_hash


def test_amend_refuses_maintainer_sourced_rules_too(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """「系统映射」 comes from the maintainer's config, never from a request."""
    workflow, _ = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    with pytest.raises(WorkflowStateError):
        workflow.amend(
            ALICE,
            draft.draft_id,
            expected_version=draft.version,
            rules=(Rule("variant", "registered", RuleSource.MAINTAINER),),
        )


# ------------------------------------------------------------ K5: 依据失效


class StubRefChecker:
    """Reports a scripted status for every ref; counts how often it was asked."""

    def __init__(self, status: object) -> None:
        self.status = status
        self.calls = 0

    def check_refs(self, scope: object, refs: tuple) -> tuple:  # type: ignore[type-arg]
        self.calls += 1
        return tuple(self.status for _ in refs)


def _doc_backed(tmp_path: Path, status: object) -> tuple[QueryWorkflow, CountingExecutor, object]:
    from queryagent.knowledge.models import RefStatus  # noqa: F401

    executor = CountingExecutor()
    checker = StubRefChecker(status)
    workflow = QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(StubMetricStore((NEW_USERS, GMV))),
        compiler=TemplateCompiler(TEMPLATES),
        executor=executor.run,
        clock=lambda: datetime(2026, 9, 9, tzinfo=timezone.utc),
        ref_checker=checker,
    )
    return workflow, executor, checker


def _confirmed_doc_draft(workflow: QueryWorkflow):  # type: ignore[no-untyped-def]
    """A draft whose chosen variant carries a document citation."""
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = workflow.amend(
        ALICE,
        draft.draft_id,
        expected_version=draft.version,
        rules=(Rule("variant", "registered", RuleSource.USER),),
    )
    return draft, amended


def test_evidence_withdrawn_before_confirming_refuses_and_expires(tmp_path: Path) -> None:
    """K5/T07: what the sheet cited is gone; it cannot be confirmed."""
    from queryagent.knowledge.models import RefStatus

    workflow, executor, checker = _doc_backed(tmp_path, RefStatus.UNAVAILABLE)
    draft, amended = _confirmed_doc_draft(workflow)
    workflow.attach_evidence(ALICE, draft.draft_id, ("d1#c1@0:5",))
    with pytest.raises(ConfirmationRequired, match="依据"):
        workflow.confirm(
            ALICE,
            draft.draft_id,
            version=amended.version,
            definition_hash=amended.definition_hash,
        )
    assert workflow.get_draft(ALICE, draft.draft_id).status is DraftStatus.EXPIRED
    assert executor.executed == []


def test_expiring_a_draft_keeps_its_version_and_hash(tmp_path: Path) -> None:
    """§4.5.6: bumping the version would mask 'evidence gone' as '口径 changed'."""
    from queryagent.knowledge.models import RefStatus

    workflow, _, _ = _doc_backed(tmp_path, RefStatus.UNAVAILABLE)
    draft, amended = _confirmed_doc_draft(workflow)
    workflow.attach_evidence(ALICE, draft.draft_id, ("d1#c1@0:5",))
    with pytest.raises(ConfirmationRequired):
        workflow.confirm(
            ALICE,
            draft.draft_id,
            version=amended.version,
            definition_hash=amended.definition_hash,
        )
    expired = workflow.get_draft(ALICE, draft.draft_id)
    assert expired.version == amended.version
    assert expired.definition_hash == amended.definition_hash


def test_evidence_withdrawn_between_confirm_and_execute_runs_no_sql(
    tmp_path: Path,
) -> None:
    """The gap the second check exists for."""
    from queryagent.knowledge.models import RefStatus

    workflow, executor, checker = _doc_backed(tmp_path, RefStatus.OK)
    draft, amended = _confirmed_doc_draft(workflow)
    workflow.attach_evidence(ALICE, draft.draft_id, ("d1#c1@0:5",))
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,
        definition_hash=amended.definition_hash,
    )
    checker.status = RefStatus.CHANGED
    with pytest.raises(ConfirmationRequired):
        workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert executor.executed == []


def test_a_refused_execute_does_not_burn_the_idempotency_key(tmp_path: Path) -> None:
    """1A's property must survive the new check being inserted before claim_run."""
    from queryagent.knowledge.models import RefStatus

    workflow, executor, checker = _doc_backed(tmp_path, RefStatus.OK)
    draft, amended = _confirmed_doc_draft(workflow)
    workflow.attach_evidence(ALICE, draft.draft_id, ("d1#c1@0:5",))
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,
        definition_hash=amended.definition_hash,
    )
    checker.status = RefStatus.UNAVAILABLE
    with pytest.raises(ConfirmationRequired):
        workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert workflow.get_run_by_key(ALICE, "k1") is None


def test_a_draft_with_no_citations_never_calls_the_checker(tmp_path: Path) -> None:
    """Maintainer-only drafts have nothing to re-check; 1A behaviour unchanged."""
    from queryagent.knowledge.models import RefStatus

    workflow, executor, checker = _doc_backed(tmp_path, RefStatus.OK)
    draft, amended = _confirmed_doc_draft(workflow)
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,
        definition_hash=amended.definition_hash,
    )
    run = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert checker.calls == 0
    assert executor.executed == [run.freshness_sql, run.sql]


# --------------------------------------------------------- P1-P3: periods


def _on(tmp_path: Path, today: object, executor: CountingExecutor) -> QueryWorkflow:
    return QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(StubMetricStore((NEW_USERS, GMV)), today=lambda: today),  # type: ignore[arg-type,return-value]
        compiler=TemplateCompiler(TEMPLATES),
        executor=executor.run,
        clock=lambda: datetime(2026, 9, 10, tzinfo=timezone.utc),
    )


def test_the_questions_time_words_become_an_absolute_period_marked_as_the_users(
    tmp_path: Path,
) -> None:
    """P1: the user asked for it; they confirm the dates it resolves to."""
    from datetime import date

    from queryagent.workflow.models import PERIOD_RULE_KEY

    draft = _on(tmp_path, date(2026, 9, 10), CountingExecutor()).prepare(
        ALICE, "上个月新增用户多少？", request_id="r1"
    )
    rule = draft.definition.rule(PERIOD_RULE_KEY)
    assert rule is not None
    assert rule.value == "2026-08-01..2026-08-31"
    assert rule.source is RuleSource.USER
    assert "上个月" in rule.note


def test_two_periods_in_one_question_leave_the_period_missing(tmp_path: Path) -> None:
    """P2: even though this metric does not require one — running without it
    would answer a different question."""
    from datetime import date

    from queryagent.workflow.models import PERIOD_RULE_KEY

    draft = _on(tmp_path, date(2026, 9, 10), CountingExecutor()).prepare(
        ALICE, "上个月和本月新增用户多少？", request_id="r1"
    )
    assert draft.definition.rule(PERIOD_RULE_KEY) is None
    assert PERIOD_RULE_KEY in draft.definition.missing


def test_a_confirmation_made_today_runs_todays_dates_tomorrow(tmp_path: Path) -> None:
    """P3: 「上个月」 confirmed on 9-10 is August, still August when run on 10-02."""
    from datetime import date

    first = _on(tmp_path, date(2026, 9, 10), CountingExecutor())
    draft = first.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    amended = _pick_registered(first, draft.draft_id)
    confirmation = first.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,  # type: ignore[union-attr]
        definition_hash=amended.definition_hash,  # type: ignore[union-attr]
    )
    executor = CountingExecutor()
    run = _on(tmp_path, date(2026, 10, 2), executor).execute(
        ALICE, confirmation.confirmation_id, idempotency_key="k1"
    )
    assert "created_at >= ? AND created_at < ?" in run.sql
    assert run.params == ("2026-08-01", "2026-09-01")
    # The freshness probe binds nothing; the query binds exactly what was recorded.
    assert executor.bound == [(), run.params]
    reread = _on(tmp_path, date(2026, 10, 2), CountingExecutor()).get_run(ALICE, run.run_id)
    assert reread.params == run.params


def test_changing_the_period_after_confirmation_invalidates_it(tmp_path: Path) -> None:
    """P3: the period is in the hash like every other semantic rule."""
    from datetime import date

    from queryagent.workflow.models import PERIOD_RULE_KEY

    workflow = _on(tmp_path, date(2026, 9, 10), CountingExecutor())
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
        rules=(Rule(PERIOD_RULE_KEY, "2026-07-01..2026-07-31", RuleSource.USER),),
    )
    with pytest.raises(ConfirmationRequired):
        workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")


# --------------------------------------------------------- T37: freshness


def _execute_registered(workflow: QueryWorkflow, question: str = "上个月新增用户多少？"):  # type: ignore[no-untyped-def]
    draft = workflow.prepare(ALICE, question, request_id="r1")
    amended = _pick_registered(workflow, draft.draft_id)
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,  # type: ignore[union-attr]
        definition_hash=amended.definition_hash,  # type: ignore[union-attr]
    )
    return workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")


def test_a_run_records_how_far_the_data_behind_it_reaches(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """F4: probed after the confirmation, before the query, and kept on the run."""
    workflow, executor = parts
    run = _execute_registered(workflow)
    assert run.freshness_sql == "SELECT MAX(created_at) FROM users"
    assert run.data_through == "2026-08-22"
    assert executor.executed == [run.freshness_sql, run.sql]
    assert workflow.get_run(ALICE, run.run_id).data_through == "2026-08-22"


def test_a_failing_probe_costs_the_note_not_the_confirmed_number(tmp_path: Path) -> None:
    class ProbeFails(CountingExecutor):
        def run(self, query: CompiledQuery) -> QueryResult:
            if query.sql.startswith("SELECT MAX("):
                raise RuntimeError("probe timed out")
            return super().run(query)

    executor = ProbeFails()
    workflow = QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(StubMetricStore((NEW_USERS, GMV))),
        compiler=TemplateCompiler(TEMPLATES),
        executor=executor.run,
    )
    run = _execute_registered(workflow)
    assert run.status is RunStatus.SUCCEEDED
    assert run.rows == ((42,),)
    assert run.freshness_sql and run.data_through == ""  # probed, and said to be unknown


def test_a_whole_statement_mapping_is_not_probed(tmp_path: Path) -> None:
    """Nothing to read a date from, so nothing runs and nothing is claimed."""
    executor = CountingExecutor()
    workflow = QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(StubMetricStore((NEW_USERS, GMV))),
        compiler=TemplateCompiler({("new_users", "registered"): "SELECT COUNT(*) AS n FROM users"}),
        executor=executor.run,
    )
    run = _execute_registered(workflow, "新增用户多少？")
    assert run.freshness_sql == ""
    assert executor.executed == [run.sql]


# ------------------------------------------------- T39: one act, one answer


def test_adopting_one_reading_and_choosing_another_in_one_amendment_is_refused(
    parts: tuple[QueryWorkflow, CountingExecutor],
) -> None:
    """F13 in the service, for every caller: the CLI is not the only door."""
    workflow, executor = parts
    draft = workflow.prepare(ALICE, "上个月新增用户多少？", request_id="r1")
    adopted = Rule(
        "counting_basis",
        "按首单日期计数",
        RuleSource.USER,
        evidence_ref="d2#c2@0:9",
        implies=("first_order",),
    )
    with pytest.raises(WorkflowStateError, match="矛盾"):
        workflow.amend(
            ALICE,
            draft.draft_id,
            expected_version=draft.version,
            rules=(adopted, Rule("variant", "registered", RuleSource.USER)),
        )
    assert workflow.get_draft(ALICE, draft.draft_id).version == draft.version
    assert executor.executed == []
