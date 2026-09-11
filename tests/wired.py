"""A wired workflow over a tiny SQLite file, shared by the MCP and confirmation-page tests.

Every statement the workflow runs is counted, because most assertions in
those tests are about statements that must not run.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from queryagent.connectors.base import QueryResult
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.mcp.tools import make_server
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import CompiledQuery, TemplateCompiler
from queryagent.workflow.execution import make_connector_executor
from queryagent.workflow.mappings import load_mappings
from queryagent.workflow.models import ActorContext, Channel
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore
from queryagent.workflow.wiring import WorkflowWiring

AGENT = ActorContext(subject_id="alice", workspace_id="ops", channel=Channel.MCP)
ALICE = ActorContext(subject_id="alice", workspace_id="ops")
ALICE_WEB = ActorContext(subject_id="alice", workspace_id="ops", channel=Channel.WEB)

METRICS = """\
metrics:
  - name: new_users
    display_name: 新增用户
    definition: 统计新加入的用户数；归属日期取法见 variants。
    tables: [users]
    variants:
      - key: registered
        label: 注册口径
        definition: 按 created_at 归属日期计数
      - key: first_order
        label: 首单口径
        definition: 按 first_order_at 归属日期计数
"""

MAPPINGS = """\
mappings:
  - metric: new_users
    variant: registered
    sql: SELECT COUNT(*) AS n FROM users
  - metric: new_users
    variant: first_order
    sql: SELECT COUNT(*) AS n FROM users WHERE first_order_at IS NOT NULL
"""


class Parts:
    """The workflow, its MCP server and the files behind them, under one directory."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path
        db = tmp_path / "shop.db"
        if not db.exists():
            connection = sqlite3.connect(db)
            connection.execute("CREATE TABLE users (id INTEGER, first_order_at TEXT)")
            connection.executemany(
                "INSERT INTO users VALUES (?,?)", [(1, "2026-01-01"), (2, None), (3, None)]
            )
            connection.commit()
            connection.close()
        (tmp_path / "metrics.yaml").write_text(METRICS, encoding="utf-8")
        (tmp_path / "mappings.yaml").write_text(MAPPINGS, encoding="utf-8")
        self.db = db
        self.state = tmp_path / "wf.db"
        self.store = SqliteWorkflowStore(self.state)
        self.connector = SQLiteConnector(path=str(db))
        real = make_connector_executor(self.connector, timeout_s=5, max_rows=100)
        self.executed: list[str] = []

        def counting(query: CompiledQuery) -> QueryResult:
            self.executed.append(query.sql)
            return real(query)

        metrics = YamlMetricStore(tmp_path / "metrics.yaml")
        self.workflow = QueryWorkflow(
            store=self.store,
            builder=MetricDraftBuilder(metrics),
            compiler=TemplateCompiler(load_mappings(tmp_path / "mappings.yaml")),
            executor=counting,
        )
        self.wiring = WorkflowWiring(
            workflow=self.workflow,
            metrics=metrics,
            dimensions=(),
            provider=None,
            today=lambda: date(2026, 9, 10),
            notices=(),
        )
        self.server = make_server(self.wiring, AGENT)

    def close(self) -> None:
        self.connector.close()
        self.store.close()

    def confirmations(self) -> list[tuple[str, str]]:
        """(draft_id, channel) of every confirmation in the state file."""
        with sqlite3.connect(self.state) as connection:
            return list(connection.execute("SELECT draft_id, channel FROM confirmations"))

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """One MCP tools/call, as a host would send it."""
        reply = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        assert reply is not None
        return reply

    def agent_prepares(self, *, variant: str = "registered") -> dict[str, Any]:
        """What an agent does before asking its person to confirm: prepare, then fill the gap."""
        prepared = self.call("prepare_query", {"question": "新增用户有多少？"})
        draft = prepared["result"]["structuredContent"]
        if not variant:
            return draft
        amended = self.call(
            "amend_query",
            {
                "draft_id": draft["draft_id"],
                "expected_version": draft["version"],
                "variant": variant,
            },
        )
        return amended["result"]["structuredContent"]

    def write_config(self) -> Path:
        """A config.yaml over the same files, for driving the CLI."""
        path = self.root / "config.yaml"
        path.write_text(
            "llm:\n  backend: openai_compatible\n  model: m\n  base_url: https://example.invalid\n"
            f"database:\n  type: sqlite\n  path: {self.db}\n"
            f"metrics_path: {self.root / 'metrics.yaml'}\n"
            f"workflow:\n  mappings_path: {self.root / 'mappings.yaml'}\n"
            f"  state_path: {self.state}\n"
            "trace: false\n",
            encoding="utf-8",
        )
        return path
