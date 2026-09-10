"""End to end: the confirmed 口径, including its period, is the number the user gets.

Runs against the real demo SQLite database, through the real connector and
safety layer, using the shipped ``examples/metrics.yaml`` and
``examples/query_mappings.yaml`` — the doubles in test_workflow_service.py
prove the gate, this proves the chain behind it is wired to real data.

"Today" is fixed at 2026-09-10 so 「上个月」 is August 2026 whatever day this
runs. Reference numbers come from SQLite's own ``strftime`` rather than from
the compiler's half-open bounds, so the test cannot pass by agreeing with
itself.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.execution import make_connector_executor
from queryagent.workflow.mappings import load_mappings
from queryagent.workflow.models import (
    PERIOD_RULE_KEY,
    ActorContext,
    DraftStatus,
    QueryRun,
    Rule,
    RuleSource,
)
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

DEMO_DB = Path("examples/demo_ecommerce/demo_shop.db")
ALICE = ActorContext(subject_id="alice", workspace_id="ops")
TODAY = date(2026, 9, 10)

REFERENCE = {
    "registered": "SELECT COUNT(*) FROM users WHERE channel <> 'internal_test' "
    "AND strftime('%Y-%m', created_at) = '2026-08'",
    "first_order": "SELECT COUNT(*) FROM users WHERE first_order_at IS NOT NULL "
    "AND channel <> 'internal_test' AND strftime('%Y-%m', first_order_at) = '2026-08'",
}


@pytest.fixture
def workflow(tmp_path: Path) -> QueryWorkflow:
    if not DEMO_DB.exists():  # pragma: no cover - depends on `make demo-data`
        pytest.skip(f"demo database not built: {DEMO_DB}")
    connector = SQLiteConnector(path=str(DEMO_DB))
    return QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(YamlMetricStore("examples/metrics.yaml"), today=lambda: TODAY),
        compiler=TemplateCompiler(load_mappings("examples/query_mappings.yaml")),
        executor=make_connector_executor(connector, timeout_s=10, max_rows=200),
    )


def _run(workflow: QueryWorkflow, variant: str, key: str) -> QueryRun:
    draft = workflow.prepare(ALICE, "上个月新增用户有多少？", request_id=f"req-{variant}")
    # The period came from the question; the reading still has to be chosen.
    assert draft.definition.rule(PERIOD_RULE_KEY).value == "2026-08-01..2026-08-31"  # type: ignore[union-attr]
    assert draft.status is DraftStatus.NEEDS_INPUT
    assert {c.label for c in draft.definition.candidates} == {"注册口径", "首单口径"}
    amended = workflow.amend(
        ALICE,
        draft.draft_id,
        expected_version=draft.version,
        rules=(Rule("variant", variant, RuleSource.USER),),
    )
    confirmation = workflow.confirm(
        ALICE,
        draft.draft_id,
        version=amended.version,
        definition_hash=amended.definition_hash,
    )
    return workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key=key)


def test_last_month_under_each_reading_is_last_months_real_number(
    workflow: QueryWorkflow,
) -> None:
    """Same question, two 口径, two numbers — both bounded to August."""
    connection = sqlite3.connect(DEMO_DB)
    expected = {name: connection.execute(sql).fetchone()[0] for name, sql in REFERENCE.items()}
    everyone = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    connection.close()

    assert _run(workflow, "registered", "k-reg").rows[0] == (expected["registered"],)
    assert _run(workflow, "first_order", "k-fo").rows[0] == (expected["first_order"],)
    assert expected["registered"] != expected["first_order"]  # otherwise nothing is shown
    assert 0 < expected["registered"] < everyone  # a window, not the all-time count


def test_the_run_dates_the_data_it_counted(workflow: QueryWorkflow) -> None:
    """F4 on the real data: the demo ends before August does, and the run knows where."""
    connection = sqlite3.connect(DEMO_DB)
    newest = connection.execute("SELECT date(MAX(created_at)) FROM users").fetchone()[0]
    connection.close()
    run = _run(workflow, "registered", "k-fresh")
    assert run.data_through == newest
