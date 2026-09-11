"""Slice 1D/1E: the sheet can say how far the data reaches before anyone confirms (T41).

The declared cadence, the opt-in probe, and the result's lag note. ADR-010 is
the rule being narrowed, so the assertions that matter most count the
statements run before a confirmation. The coverage note after execution is
test_coverage.py's.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from queryagent.budget import SqliteBudgetLedger
from queryagent.cli import main
from queryagent.config import BudgetConfig, load_config
from queryagent.connectors.base import QueryResult
from queryagent.metrics.base import Metric, MetricVariant
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import CompiledQuery, TemplateCompiler
from queryagent.workflow.freshness import (
    DECLARED,
    OFF,
    PROBE,
    PROBE_FAILED,
    FreshnessPolicy,
    describe_lag,
)
from queryagent.workflow.mappings import QueryMapping, load_mappings
from queryagent.workflow.models import ActorContext
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

ALICE = ActorContext(subject_id="alice", workspace_id="ops")
SHANGHAI = ZoneInfo("Asia/Shanghai")
TODAY = date(2026, 9, 11)
NOON = datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc)  # 12:00 in Shanghai

GMV = Metric(name="gmv", display_name="成交额", definition="订单金额求和。")
NEW_USERS = Metric(
    name="new_users",
    display_name="新增用户",
    definition="统计新加入的用户数。",
    variants=(
        MetricVariant("registered", "注册口径", "按 created_at 归属日期"),
        MetricVariant("first_order", "首单口径", "按 first_order_at 归属日期"),
    ),
)
NEW_USERS_MAPPINGS = {
    ("new_users", "registered"): QueryMapping(
        source="users", measure="COUNT(*)", label="n", time_column="created_at", lag_days=1
    ),
    ("new_users", "first_order"): QueryMapping(
        source="users", measure="COUNT(*)", label="n", time_column="first_order_at", lag_days=1
    ),
}


class _Metrics:
    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        return [m for m in (GMV, NEW_USERS) if m.display_name in question]

    def get(self, name: str) -> Metric | None:
        return next((m for m in (GMV, NEW_USERS) if m.name == name), None)


class Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


class Probe:
    """The short-timeout executor a ``probe`` policy holds; counts what it is asked."""

    def __init__(self, latest: str = "2026-08-22 10:00:00") -> None:
        self.latest = latest
        self.executed: list[str] = []

    def run(self, query: CompiledQuery) -> QueryResult:
        self.executed.append(query.sql)
        return QueryResult(("latest",), ((self.latest,),), elapsed_ms=1, truncated=False)


class Business:
    """The executor for confirmed runs. Its probe answers too — at execution time."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def run(self, query: CompiledQuery) -> QueryResult:
        self.executed.append(query.sql)
        if query.sql.startswith("SELECT MAX("):
            return QueryResult(("latest",), (("2026-08-30",),), elapsed_ms=1, truncated=False)
        return QueryResult(("gmv",), ((1.0,),), elapsed_ms=1, truncated=False)


def _workflow(
    tmp_path: Path,
    policy: FreshnessPolicy,
    *,
    lag_days: int | None = None,
    clock: Clock | None = None,
    budget: SqliteBudgetLedger | None = None,
) -> tuple[QueryWorkflow, Business]:
    business = Business()
    mappings = {
        ("gmv", ""): QueryMapping(
            source="orders",
            measure="SUM(amount)",
            label="gmv",
            time_column="created_at",
            lag_days=lag_days,
        ),
        **NEW_USERS_MAPPINGS,
    }
    workflow = QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(_Metrics(), today=lambda: TODAY),
        compiler=TemplateCompiler(mappings),
        executor=business.run,
        clock=clock or Clock(NOON),
        budget=budget,
        freshness=policy,
    )
    return workflow, business


def _probing(probe: Probe) -> FreshnessPolicy:
    return FreshnessPolicy(mode=PROBE, today=lambda: TODAY, probe=probe.run, zone=SHANGHAI)


DECLARING = FreshnessPolicy(mode=DECLARED, today=lambda: TODAY)


# ---------------------------------------------------------------- declared


def test_a_declared_cadence_warns_on_the_sheet_and_runs_nothing(tmp_path: Path) -> None:
    """G8/G11: T+1 on 2026-09-11 means data to 09-10; the rest of September is not there."""
    workflow, business = _workflow(tmp_path, DECLARING, lag_days=1)
    draft = workflow.prepare(ALICE, "9月成交额", request_id="r1")
    assert workflow.freshness_advisory(ALICE, draft.draft_id) == (
        "维护者声明该表按 T+1 更新，预计最新数据到 2026-09-10：统计区间最后 20 天"
        "（2026-09-11 起）可能还没有数据。",
    )
    assert business.executed == []


def test_a_period_the_cadence_already_covers_gets_no_note(tmp_path: Path) -> None:
    workflow, _ = _workflow(tmp_path, DECLARING, lag_days=1)
    draft = workflow.prepare(ALICE, "上个月成交额", request_id="r1")
    assert workflow.freshness_advisory(ALICE, draft.draft_id) == ()


def test_before_a_reading_is_chosen_each_readings_table_is_named(tmp_path: Path) -> None:
    """Two readings over two columns may reach different dates; say which is which."""
    workflow, _ = _workflow(tmp_path, DECLARING)
    draft = workflow.prepare(ALICE, "9月新增用户", request_id="r1")
    notes = workflow.freshness_advisory(ALICE, draft.draft_id)
    assert [note.split("：")[0] for note in notes] == ["users.created_at", "users.first_order_at"]


def test_off_says_nothing_before_confirmation(tmp_path: Path) -> None:
    workflow, _ = _workflow(tmp_path, FreshnessPolicy(mode=OFF, today=lambda: TODAY), lag_days=1)
    draft = workflow.prepare(ALICE, "9月成交额", request_id="r1")
    assert workflow.freshness_advisory(ALICE, draft.draft_id) == ()


# ------------------------------------------------------------------- probe


def test_probe_mode_runs_only_the_compilers_probe_and_once_per_cache_window(
    tmp_path: Path,
) -> None:
    """G9: before confirmation, the one statement ADR-010 allows — and not twice in ten minutes."""
    clock = Clock(NOON)
    probe = Probe()
    workflow, business = _workflow(tmp_path, _probing(probe), clock=clock)
    draft = workflow.prepare(ALICE, "9月成交额", request_id="r1")
    first = workflow.freshness_advisory(ALICE, draft.draft_id)
    again = workflow.freshness_advisory(ALICE, draft.draft_id)
    assert first == again == (
        "库中最新一条记录在 2026-08-22（12:00 探测，仅供参考），早于统计区间的开始 "
        "2026-09-01：整个区间都还没有数据。",
    )
    assert probe.executed == ["SELECT MAX(created_at) FROM orders"]
    assert business.executed == []
    clock.at += timedelta(minutes=11)
    workflow.freshness_advisory(ALICE, draft.draft_id)
    assert len(probe.executed) == 2


def test_a_probe_before_confirmation_is_charged_to_the_budget_and_stopped_by_it(
    tmp_path: Path,
) -> None:
    """G9: a statement is a statement; once the allowance is spent the note says so."""
    clock = Clock(NOON)
    ledger = SqliteBudgetLedger(
        tmp_path / "wf.db",
        BudgetConfig(max_queries_per_day=1),
        statement_timeout_s=2,
        zone=SHANGHAI,
        clock=clock,
    )
    probe = Probe()
    workflow, _ = _workflow(tmp_path, _probing(probe), clock=clock, budget=ledger)
    draft = workflow.prepare(ALICE, "9月成交额", request_id="r1")
    workflow.freshness_advisory(ALICE, draft.draft_id)
    clock.at += timedelta(minutes=11)
    assert workflow.freshness_advisory(ALICE, draft.draft_id) == (PROBE_FAILED,)
    assert len(probe.executed) == 1


def test_a_failed_probe_falls_back_to_the_declared_cadence(tmp_path: Path) -> None:
    class Broken:
        def run(self, query: CompiledQuery) -> QueryResult:
            raise TimeoutError("probe timed out")

    policy = FreshnessPolicy(mode=PROBE, today=lambda: TODAY, probe=Broken().run)
    workflow, _ = _workflow(tmp_path, policy, lag_days=1)
    draft = workflow.prepare(ALICE, "9月成交额", request_id="r1")
    (note,) = workflow.freshness_advisory(ALICE, draft.draft_id)
    assert note.startswith("维护者声明该表按 T+1 更新")


def test_what_a_probe_said_before_confirmation_is_not_what_was_confirmed(tmp_path: Path) -> None:
    """G10: data loads between the sheet and the run; the confirmation still holds,
    and the result reports the probe taken when the query ran."""
    clock = Clock(NOON)
    probe = Probe()
    workflow, _ = _workflow(tmp_path, _probing(probe), clock=clock)
    draft = workflow.prepare(ALICE, "上个月成交额", request_id="r1")
    assert "2026-08-22" in workflow.freshness_advisory(ALICE, draft.draft_id)[0]
    confirmation = workflow.confirm(
        ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    probe.latest = "2026-08-31 23:00:00"
    clock.at += timedelta(minutes=11)
    assert "2026-08-31" in workflow.freshness_advisory(ALICE, draft.draft_id)[0]
    assert workflow.get_draft(ALICE, draft.draft_id).definition_hash == draft.definition_hash
    run = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert run.data_through == "2026-08-30"


# ----------------------------------------------------------------- the lag


def test_data_older_than_the_declared_cadence_is_named_on_the_result(tmp_path: Path) -> None:
    """G11: T+1 expected 09-10 when it ran; the newest record is 08-30."""
    workflow, _ = _workflow(tmp_path, DECLARING, lag_days=1)
    draft = workflow.prepare(ALICE, "上个月成交额", request_id="r1")
    confirmation = workflow.confirm(
        ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    run = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert workflow.get_run(ALICE, run.run_id).expected_through == "2026-09-10"
    assert describe_lag(run.expected_through, run.data_through) == (
        "数据比维护者声明的更新节奏滞后 11 天：按声明应有到 2026-09-10 的数据，"
        "库中最新一条记录在 2026-08-30，可能是数据加载延迟。"
    )


def test_without_a_declared_cadence_nothing_is_expected(tmp_path: Path) -> None:
    workflow, _ = _workflow(tmp_path, DECLARING)
    draft = workflow.prepare(ALICE, "上个月成交额", request_id="r1")
    confirmation = workflow.confirm(
        ALICE, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    run = workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key="k1")
    assert run.expected_through == ""
    assert describe_lag(run.expected_through, run.data_through) == ""


# ------------------------------------------------------------------ config

STRUCTURED = """\
mappings:
  - metric: gmv
    from: orders
    measure: SUM(amount)
    label: gmv
{time_column}    freshness: {freshness}
"""


@pytest.mark.parametrize(
    ("freshness", "complaint"),
    [
        ("{lag_days: -1}", "0 or more"),
        ("{lag_days: soon}", "0 or more"),
        ("{lag: 1}", "lag_days: N"),
    ],
)
def test_a_declared_cadence_must_be_whole_days(
    tmp_path: Path, freshness: str, complaint: str
) -> None:
    path = tmp_path / "m.yaml"
    text = STRUCTURED.format(time_column="    time_column: created_at\n", freshness=freshness)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=complaint):
        load_mappings(path)


def test_a_cadence_without_a_time_column_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "m.yaml"
    path.write_text(STRUCTURED.format(time_column="", freshness="{lag_days: 1}"), encoding="utf-8")
    with pytest.raises(ValueError, match="needs a 'time_column'"):
        load_mappings(path)


CONFIG = """\
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
{extra}trace: false
"""


def test_the_default_is_the_declared_cadence_and_an_unknown_mode_is_refused(
    tmp_path: Path,
) -> None:
    fields = {"db": "x.db", "metrics": "m.yaml", "mappings": "q.yaml", "state": "s.db"}
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG.format(**fields, extra=""), encoding="utf-8")
    assert load_config(path).workflow.freshness_before_confirm == "declared"
    extra = "  freshness_before_confirm: sometimes\n"
    path.write_text(CONFIG.format(**fields, extra=extra), encoding="utf-8")
    with pytest.raises(ValueError, match="freshness_before_confirm"):
        load_config(path)


def test_the_flow_prints_the_cadence_note_below_the_sheet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through main(), with the product's own wiring. A cadence of 100 000 days
    keeps the expected date far behind any real today, so the note is stable."""
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE orders (created_at TEXT, amount REAL)")
    connection.execute("INSERT INTO orders VALUES ('2026-08-05', 3.0)")
    connection.commit()
    connection.close()
    (tmp_path / "metrics.yaml").write_text(
        "metrics:\n  - name: gmv\n    display_name: 成交额\n    definition: 订单金额求和。\n",
        encoding="utf-8",
    )
    (tmp_path / "mappings.yaml").write_text(
        STRUCTURED.format(
            time_column="    time_column: created_at\n", freshness="{lag_days: 100000}"
        ),
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        CONFIG.format(
            db=tmp_path / "shop.db",
            metrics=tmp_path / "metrics.yaml",
            mappings=tmp_path / "mappings.yaml",
            state=tmp_path / "workflow.db",
            extra="",
        ),
        encoding="utf-8",
    )
    code = main(
        ["flow", "成交额是多少？", "--config", str(config), "--period", "2026-08-01..2026-08-31",
         "--yes"]
    )  # fmt: skip
    assert code == 0
    sheet, _, result = capsys.readouterr().out.partition("结果（")
    assert "数据新鲜度（确认前的参考，不属于口径）" in sheet
    assert "维护者声明该表按 T+100000 更新" in sheet
    assert "整个统计区间可能都还没有数据" in sheet
    assert "3.0" in result


def test_probe_mode_through_main_probes_before_confirmation_and_runs_nothing_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """G9 with the product's own short-timeout executor — found in review that only a
    fake probe had been tested. Declined: the probe ran, the query did not."""
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE orders (created_at TEXT, amount REAL)")
    connection.execute("INSERT INTO orders VALUES ('2026-08-05', 3.0)")
    connection.commit()
    connection.close()
    (tmp_path / "metrics.yaml").write_text(
        "metrics:\n  - name: gmv\n    display_name: 成交额\n    definition: 订单金额求和。\n",
        encoding="utf-8",
    )
    (tmp_path / "mappings.yaml").write_text(
        "mappings:\n  - metric: gmv\n    from: orders\n    measure: SUM(amount)\n"
        "    label: gmv\n    time_column: created_at\n",
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        CONFIG.format(
            db=tmp_path / "shop.db",
            metrics=tmp_path / "metrics.yaml",
            mappings=tmp_path / "mappings.yaml",
            state=tmp_path / "workflow.db",
            extra="  freshness_before_confirm: probe\n",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    code = main(
        ["flow", "成交额是多少？", "--config", str(config), "--period", "2026-08-01..2026-08-31"]
    )
    assert code == 2
    assert "库中最新一条记录在 2026-08-05" in capsys.readouterr().out
    state = sqlite3.connect(tmp_path / "workflow.db")
    assert state.execute("SELECT COUNT(*) FROM runs").fetchone() == (0,)
    assert state.execute("SELECT latest FROM freshness_cache").fetchall() == [("2026-08-05",)]
    state.close()
