"""Slice 1E: totals a maintainer sets and nothing else can raise (T40).

Config parsing, the ledger's counting, the flow's admission order, the agent
path's per-question cap and the CLI's exit codes, in that order. The
engine-enforced scan limit needs a live ClickHouse and is in
test_clickhouse_integration.py.
"""

from __future__ import annotations

import contextlib
import inspect
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from queryagent.budget import (
    LEASE_MARGIN_S,
    Budget,
    BudgetedConnector,
    BudgetExceeded,
    SqliteBudgetLedger,
    Unmetered,
)
from queryagent.cli import _explain, _make_run_question, main
from queryagent.config import BudgetConfig, load_config
from queryagent.connectors.base import QueryResult
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.llm.base import Message, ModelResponse, ToolCall
from queryagent.metrics.base import Metric
from queryagent.schema import TableSchema
from queryagent.tools import ToolRegistry, make_default_tools
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import CompiledQuery, TemplateCompiler
from queryagent.workflow.mappings import QueryMapping
from queryagent.workflow.models import ActorContext
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

ALICE = ActorContext(subject_id="alice", workspace_id="ops")
SHANGHAI = ZoneInfo("Asia/Shanghai")
NOON_AUG_31 = datetime(2026, 8, 31, 4, 0, tzinfo=timezone.utc)  # 12:00 in Shanghai

SQLITE_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: shop.db
"""

CLICKHOUSE_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: clickhouse
  host: 127.0.0.1
  database: demo_shop
"""


def _config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------ config


def test_without_a_budget_section_there_are_no_totals(tmp_path: Path) -> None:
    """G1: the rollback path is the absence of the section, not a flag."""
    assert load_config(_config(tmp_path, SQLITE_CONFIG)).budget is None


def test_a_budget_section_is_read_as_limits_and_what_it_omits_stays_unlimited(
    tmp_path: Path,
) -> None:
    text = SQLITE_CONFIG + "budget:\n  max_queries_per_day: 50\n  max_concurrent: 2\n"
    config = load_config(_config(tmp_path, text))
    assert config.budget == BudgetConfig(max_queries_per_day=50, max_concurrent=2)


@pytest.mark.parametrize(
    ("entry", "complaint"),
    [
        ("max_querys_per_day: 5", "unknown keys"),
        ("max_concurrent: 0", "positive integer"),
        ("max_concurrent: true", "positive integer"),
    ],
)
def test_a_budget_entry_that_would_limit_nothing_is_refused_at_load(
    tmp_path: Path, entry: str, complaint: str
) -> None:
    with pytest.raises(ValueError, match=complaint):
        load_config(_config(tmp_path, SQLITE_CONFIG + f"budget:\n  {entry}\n"))


def test_a_scan_limit_is_refused_where_the_database_cannot_enforce_it(tmp_path: Path) -> None:
    """G6/E03: a limit written down but not applied is a false statement."""
    with pytest.raises(ValueError, match="cannot be enforced on sqlite"):
        load_config(_config(tmp_path, SQLITE_CONFIG + "budget:\n  max_rows_scanned: 1000\n"))
    text = CLICKHOUSE_CONFIG + "budget:\n  max_rows_scanned: 1000\n"
    budget = load_config(_config(tmp_path, text)).budget
    assert budget is not None and budget.max_rows_scanned == 1000


# ------------------------------------------------------------------ ledger


class Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


def _ledger(tmp_path: Path, clock: Clock, **limits: int) -> SqliteBudgetLedger:
    return SqliteBudgetLedger(
        tmp_path / "wf.db",
        BudgetConfig(**limits),
        statement_timeout_s=10,
        zone=SHANGHAI,
        clock=clock,
    )


def test_a_request_needing_more_statements_than_one_request_may_run_is_refused(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path, Clock(NOON_AUG_31), max_queries_per_request=1)
    with pytest.raises(BudgetExceeded, match="max_queries_per_request"):
        ledger.admit("alice", queries=2)
    with ledger.admit("alice", queries=1):
        pass


def test_the_daily_allowance_is_per_subject_and_per_business_day(tmp_path: Path) -> None:
    clock = Clock(NOON_AUG_31)
    ledger = _ledger(tmp_path, clock, max_queries_per_day=3)
    with ledger.admit("alice", queries=2):
        pass
    with ledger.admit("alice", queries=1):
        pass
    with pytest.raises(BudgetExceeded, match="max_queries_per_day") as refused:
        ledger.admit("alice", queries=1)
    assert refused.value.retryable is False
    assert "2026-09-01 00:00（Asia/Shanghai）恢复" in str(refused.value)
    # The refusal reserved nothing: a ledger allowing one more admits exactly one.
    roomier = _ledger(tmp_path, clock, max_queries_per_day=4)
    with roomier.admit("alice", queries=1):
        pass
    with pytest.raises(BudgetExceeded, match="max_queries_per_day"):
        roomier.admit("alice", queries=1)
    with ledger.admit("bob", queries=3):  # someone else's allowance is their own
        pass
    clock.at = datetime(2026, 8, 31, 16, 30, tzinfo=timezone.utc)  # 00:30 on 09-01 in Shanghai
    with ledger.admit("alice", queries=3):
        pass


def test_time_already_spent_today_stops_the_next_statement(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, Clock(NOON_AUG_31), max_query_seconds_per_day=2)
    with ledger.admit("alice", queries=1) as lease:
        lease.record(2_500)
    with pytest.raises(BudgetExceeded, match="max_query_seconds_per_day"):
        ledger.admit("alice", queries=1)


def test_the_concurrency_limit_holds_across_two_processes_sharing_the_state_file(
    tmp_path: Path,
) -> None:
    """G4: two ledgers on one file stand in for two CLI processes."""
    clock = Clock(NOON_AUG_31)
    first = _ledger(tmp_path, clock, max_concurrent=1)
    second = _ledger(tmp_path, clock, max_concurrent=1)
    with first.admit("alice", queries=1):
        with pytest.raises(BudgetExceeded, match="max_concurrent") as refused:
            second.admit("bob", queries=1)
        assert refused.value.retryable is True
        # E06: and when — the lease's expiry is the latest the slot can take.
        assert "最迟约 15 秒后空出" in str(refused.value)
    with second.admit("bob", queries=1):
        pass


def test_a_slot_held_by_a_process_that_died_is_freed_when_its_lease_expires(
    tmp_path: Path,
) -> None:
    """G4: a killed process never releases; its lease runs out instead."""
    clock = Clock(NOON_AUG_31)
    ledger = _ledger(tmp_path, clock, max_concurrent=1)
    ledger.admit("alice", queries=1)  # never released
    with pytest.raises(BudgetExceeded, match="max_concurrent"):
        ledger.admit("bob", queries=1)
    clock.at += timedelta(seconds=10 + LEASE_MARGIN_S + 1)
    with ledger.admit("bob", queries=1):
        pass


def test_a_refunded_lease_gives_back_the_statements_it_never_ran(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, Clock(NOON_AUG_31), max_queries_per_day=2)
    with ledger.admit("alice", queries=2) as lease:
        lease.refund()
    with ledger.admit("alice", queries=2):
        pass


# -------------------------------------------------------------------- flow

GMV = Metric(
    name="gmv", display_name="成交额", definition="status='paid' 订单的 amount 求和。"
)
MAPPINGS = {
    ("gmv", ""): QueryMapping(
        source="orders", measure="SUM(amount)", label="gmv", time_column="created_at"
    ),
}


class _GmvOnly:
    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        return [GMV]

    def get(self, name: str) -> Metric | None:
        return GMV


class CountingExecutor:
    """Every statement the flow sends, probe included."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def run(self, query: CompiledQuery) -> QueryResult:
        self.executed.append(query.sql)
        return QueryResult(columns=("v",), rows=(("2026-08-22",),), elapsed_ms=1, truncated=False)


def _workflow(tmp_path: Path, budget: Budget) -> tuple[QueryWorkflow, CountingExecutor]:
    executor = CountingExecutor()
    workflow = QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(_GmvOnly()),
        compiler=TemplateCompiler(MAPPINGS),
        executor=executor.run,
        budget=budget,
    )
    return workflow, executor


def _confirmed(workflow: QueryWorkflow) -> str:
    draft = workflow.prepare(ALICE, "成交额是多少？", request_id="r1")
    confirmation = workflow.confirm(
        ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    return confirmation.confirmation_id


def test_a_run_over_budget_executes_nothing_and_leaves_its_idempotency_key_unspent(
    tmp_path: Path,
) -> None:
    """G3: refused before the claim, so the same request can run once allowed."""
    ledger = _ledger(tmp_path, Clock(NOON_AUG_31), max_queries_per_day=1)
    workflow, executor = _workflow(tmp_path, ledger)
    confirmation_id = _confirmed(workflow)
    with pytest.raises(BudgetExceeded, match="本次还需 2 条"):
        workflow.execute(ALICE, confirmation_id, idempotency_key="k1")
    assert executor.executed == []
    assert workflow.get_run_by_key(ALICE, "k1") is None


def test_a_run_is_charged_for_its_probe_and_its_query_and_a_replay_for_nothing(
    tmp_path: Path,
) -> None:
    ledger = _ledger(tmp_path, Clock(NOON_AUG_31), max_queries_per_day=3)
    workflow, executor = _workflow(tmp_path, ledger)
    confirmation_id = _confirmed(workflow)
    first = workflow.execute(ALICE, confirmation_id, idempotency_key="k1")
    again = workflow.execute(ALICE, confirmation_id, idempotency_key="k1")
    assert again.run_id == first.run_id
    assert len(executor.executed) == 2  # probe + query, once
    with ledger.admit("alice", queries=1):  # 2 of 3 spent: the replay cost nothing
        pass
    with pytest.raises(BudgetExceeded, match="max_queries_per_day"):
        ledger.admit("alice", queries=1)


def test_without_a_budget_every_run_is_admitted(tmp_path: Path) -> None:
    """G1: no totals means the v0.8 behaviour, run after run."""
    workflow, executor = _workflow(tmp_path, Unmetered())
    confirmation_id = _confirmed(workflow)
    for key in ("k1", "k2", "k3"):
        workflow.execute(ALICE, confirmation_id, idempotency_key=key)
    assert len(executor.executed) == 6


def test_no_workflow_call_takes_a_budget_argument() -> None:
    """G2: the limits are read when the service is built; afterwards nothing reaches them."""
    for name in ("prepare", "amend", "confirm", "execute"):
        parameters = inspect.signature(getattr(QueryWorkflow, name)).parameters
        assert not any("budget" in p or p.startswith("max_") for p in parameters)
    assert not any(name.startswith("set") for name in dir(SqliteBudgetLedger))


def test_no_command_line_flag_can_raise_a_budget(capsys: pytest.CaptureFixture[str]) -> None:
    """G2: every end-user command, and none of them mentions a budget."""
    for command in ("flow", "ask", "chat"):
        with pytest.raises(SystemExit, match="^0$"):
            main([command, "--help"])
        text = capsys.readouterr().out
        assert "budget" not in text
        assert "--max-queries" not in text and "--max-concurrent" not in text


# -------------------------------------------------------------- agent path


class _FakeConnector:
    dialect = "sqlite"

    def __init__(self) -> None:
        self.executed: list[str] = []

    def get_schema(self) -> list[TableSchema]:
        return []

    def execute(
        self, sql: str, *, timeout_s: int, max_rows: int, params: object = ()
    ) -> QueryResult:
        self.executed.append(sql)
        return QueryResult(columns=("n",), rows=((1,),), elapsed_ms=1, truncated=False)

    def close(self) -> None:
        pass


def test_an_agent_question_stops_at_the_statement_cap_with_an_observation_not_a_crash(
    tmp_path: Path,
) -> None:
    """G5/E07: the model is told the budget is spent; it cannot retry past it."""
    inner = _FakeConnector()
    ledger = _ledger(tmp_path, Clock(NOON_AUG_31), max_queries_per_request=2)
    budgeted = BudgetedConnector(inner, ledger, "alice")  # type: ignore[arg-type]
    registry = ToolRegistry(make_default_tools(budgeted, timeout_s=10, max_rows=10))
    observations = [
        registry.validate_and_dispatch("execute_sql", {"sql": "SELECT 1"}) for _ in range(3)
    ]
    assert [o.is_error for o in observations] == [False, False, True]
    assert "max_queries_per_request" in observations[2].content
    assert "重试不会成功" in observations[2].content
    assert len(inner.executed) == 2
    budgeted.start_request()  # the next question has its own allowance
    assert not registry.validate_and_dispatch("execute_sql", {"sql": "SELECT 1"}).is_error


# --------------------------------------------------------------------- CLI

FLOW_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: {db}
metrics_path: {metrics}
workflow:
  mappings_path: {mappings}
  state_path: {state}
trace: false
budget:
  max_queries_per_day: 2
"""


def test_the_run_after_the_daily_allowance_is_refused_with_exit_2_and_touches_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G3 through main(): refused before the database, naming who can change it."""
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE orders (amount REAL)")
    connection.execute("INSERT INTO orders VALUES (9.5)")
    connection.commit()
    connection.close()
    (tmp_path / "metrics.yaml").write_text(
        "metrics:\n  - name: gmv\n    display_name: 成交额\n    definition: 订单金额求和。\n",
        encoding="utf-8",
    )
    (tmp_path / "mappings.yaml").write_text(
        "mappings:\n  - metric: gmv\n    sql: SELECT SUM(amount) AS gmv FROM orders\n",
        encoding="utf-8",
    )
    config = _config(
        tmp_path,
        FLOW_CONFIG.format(
            db=tmp_path / "shop.db",
            metrics=tmp_path / "metrics.yaml",
            mappings=tmp_path / "mappings.yaml",
            state=tmp_path / "workflow.db",
        ),
    )
    codes = [main(["flow", "成交额是多少？", "--config", str(config), "--yes"]) for _ in range(3)]
    assert codes == [0, 0, 2]
    err = capsys.readouterr().err
    assert "max_queries_per_day" in err and "只有维护者能调整" in err
    state = sqlite3.connect(tmp_path / "workflow.db")
    assert state.execute("SELECT COUNT(*) FROM runs").fetchone() == (2,)
    state.close()


def test_a_full_slot_is_worth_retrying_and_a_spent_allowance_is_not() -> None:
    """E06: 75 tells a script to come back later; 2 tells it not to bother."""
    assert _explain(BudgetExceeded("满", item="max_concurrent", retryable=True))[2] == 75
    assert _explain(BudgetExceeded("用完", item="max_queries_per_day"))[2] == 2


# ------------------------------------------------------ the agent's wiring

ASK_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: {db}
workflow:
  state_path: {state}
trace: false
budget:
  max_queries_per_request: 1
"""


class TwoStatements:
    """A model that runs two statements before answering — an agent exploring."""

    def __init__(self) -> None:
        self.calls: list[list[Message]] = []

    def complete(
        self, messages: list[Message], tools: object = None, **kwargs: object
    ) -> ModelResponse:
        self.calls.append(list(messages))
        step = len(self.calls)
        if step <= 2:
            # Different text, same answer: the loop stops an identical call repeated.
            sql = f"SELECT SUM(amount) FROM orders WHERE {step} = {step}"
            call = ToolCall(id=f"t{step}", name="execute_sql", arguments={"sql": sql})
            return ModelResponse(text="", tool_calls=(call,), stop_reason="tool_use")
        return ModelResponse(text="成交额 9.5", stop_reason="stop")

    def close(self) -> None:
        pass

    def tool_replies(self) -> list[str]:
        return [m.content for m in self.calls[-1] if m.tool_call_id]


def _ask_config(tmp_path: Path) -> Path:
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE orders (amount REAL)")
    connection.execute("INSERT INTO orders VALUES (9.5)")
    connection.commit()
    connection.close()
    text = ASK_CONFIG.format(db=tmp_path / "shop.db", state=tmp_path / "workflow.db")
    return _config(tmp_path, text)


def test_ask_stops_the_model_at_the_statement_cap_through_the_real_wiring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G5 through main(): the connector ask builds is the budgeted one — found in
    review that only a hand-built one was tested."""
    backend = TwoStatements()
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setattr("queryagent.cli.make_backend", lambda _config: backend)
    assert main(["ask", "成交额是多少", "--config", str(_ask_config(tmp_path))]) == 0
    first, second = backend.tool_replies()
    assert "9.5" in first
    assert "max_queries_per_request" in second
    state = sqlite3.connect(tmp_path / "workflow.db")
    assert state.execute("SELECT SUM(queries) FROM budget_ledger").fetchone() == (1,)
    state.close()


def test_eval_is_not_metered_even_with_a_budget_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E02: the eval's wiring passes no subject, so nothing is admitted or counted."""
    backend = TwoStatements()
    monkeypatch.setattr("queryagent.cli.make_backend", lambda _config: backend)
    config = load_config(_ask_config(tmp_path))
    connector = SQLiteConnector(path=str(tmp_path / "shop.db"))
    with contextlib.ExitStack() as stack:
        run_question = _make_run_question(connector, config, 8, stack)
        list(run_question("成交额是多少"))
    connector.close()
    replies = backend.tool_replies()
    assert len(replies) == 2 and all("9.5" in reply for reply in replies)
    assert not (tmp_path / "workflow.db").exists()


def test_clickhouse_names_an_exceeded_scan_limit_as_one() -> None:
    """G7 without a server: error 158 reads as the scan limit it is, stack trace cut."""
    pytest.importorskip("clickhouse_driver")
    from clickhouse_driver.errors import ServerException

    from queryagent.connectors.clickhouse import ClickHouseConnector
    from queryagent.errors import QueryError

    class Refusing:
        last_query = None

        def execute(self, *args: object, **kwargs: object) -> object:
            raise ServerException(
                "Limit for rows (controlled by 'max_rows_to_read' setting) exceeded. "
                "Stack trace: 0. DB::Exception ...",
                code=158,
            )

    connector = ClickHouseConnector(host="127.0.0.1", max_rows_scanned=1000)
    connector._client = Refusing()
    with pytest.raises(QueryError, match="超过扫描上限.*1000 行") as refused:
        connector.execute("SELECT sum(id) FROM users", timeout_s=5, max_rows=5)
    assert "Stack trace" not in str(refused.value)
