"""Slice 1A end-to-end: the confirmed 口径 is the number the user gets.

Runs against the real demo SQLite database through the real connector and
safety layer — the doubles in test_workflow_service.py prove the gate, this
proves the chain behind it is wired to an actual database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.execution import make_connector_executor
from queryagent.workflow.models import ActorContext, DraftStatus, Rule, RuleSource
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

DEMO_DB = Path("examples/demo_ecommerce/demo_shop.db")
ALICE = ActorContext(subject_id="alice", workspace_id="ops")

REGISTERED_SQL = "SELECT COUNT(*) AS 新增用户 FROM users WHERE channel <> 'internal_test'"
FIRST_ORDER_SQL = (
    "SELECT COUNT(*) AS 新增用户 FROM users "
    "WHERE first_order_at IS NOT NULL AND channel <> 'internal_test'"
)


@pytest.fixture
def workflow(tmp_path: Path) -> QueryWorkflow:
    if not DEMO_DB.exists():  # pragma: no cover - depends on `make demo-data`
        pytest.skip(f"demo database not built: {DEMO_DB}")
    connector = SQLiteConnector(path=str(DEMO_DB))
    return QueryWorkflow(
        store=SqliteWorkflowStore(tmp_path / "wf.db"),
        builder=MetricDraftBuilder(YamlMetricStore("examples/metrics.yaml")),
        compiler=TemplateCompiler(
            {
                ("new_users", "registered"): REGISTERED_SQL,
                ("new_users", "first_order"): FIRST_ORDER_SQL,
            }
        ),
        executor=make_connector_executor(connector, timeout_s=10, max_rows=200),
    )


def _run(workflow: QueryWorkflow, variant: str, key: str) -> tuple[object, ...]:
    draft = workflow.prepare(ALICE, "上个月新增用户有多少？", request_id=f"req-{variant}")
    # The metric declares two readings, so the draft arrives incomplete and
    # nothing can be confirmed until the user closes that gap.
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
    return workflow.execute(ALICE, confirmation.confirmation_id, idempotency_key=key).rows[0]


def test_the_two_confirmed_definitions_give_the_two_real_numbers(
    workflow: QueryWorkflow,
) -> None:
    """The product's whole premise: same question, two 口径, two numbers."""
    connection = sqlite3.connect(DEMO_DB)
    expected_registered = connection.execute(REGISTERED_SQL.replace("新增用户", "n")).fetchone()[0]
    expected_first_order = connection.execute(FIRST_ORDER_SQL.replace("新增用户", "n")).fetchone()[
        0
    ]
    connection.close()

    assert _run(workflow, "registered", "k-reg") == (expected_registered,)
    assert _run(workflow, "first_order", "k-fo") == (expected_first_order,)
    assert expected_registered != expected_first_order  # otherwise the demo proves nothing
