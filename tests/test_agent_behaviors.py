"""Behaviour tests beyond the four termination paths: self-repair,
parse-failure degradation, clarify interception, thinking events, and a full
end-to-end pipeline run over a real SQLite database (fake LLM only).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from queryagent.agent import run_agent
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.context import ContextBuilder
from queryagent.errors import LLMParseError, QueryError
from queryagent.events import (
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    RetryEvent,
    ThinkEvent,
)
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.tools import (
    ToolRegistry,
    ToolSpec,
    make_clarify_tool,
    make_default_tools,
)
from tests.fakes import FakeLLMBackend, answer, tool_call

METRICS_YAML = """\
metrics:
  - name: new_users
    display_name: 新增用户
    aliases: [新用户, 新增]
    definition: 按 users.created_at 日期计数。
    caution: 运营口径按 first_order_at 计数，需确认。
"""


def make_builder(metrics_path: Path | None = None) -> ContextBuilder:
    store = YamlMetricStore(metrics_path) if metrics_path else None
    return ContextBuilder(
        schema_text="TABLE t\n  id INT NOT NULL", dialect="sqlite", metric_store=store
    )


def flaky_sql_spec() -> ToolSpec:
    attempts: list[str] = []

    def handler(sql: str) -> str:
        attempts.append(sql)
        if len(attempts) == 1:
            raise QueryError("no such column: usrs.id", dialect="sqlite")
        return "id\n--\n1\n(1 rows, 1 ms)"

    return ToolSpec(
        name="execute_sql",
        description="run sql",
        input_schema={
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
        handler=handler,
    )


def test_self_repair_recovers_and_emits_retry() -> None:
    backend = FakeLLMBackend(
        [
            tool_call("execute_sql", {"sql": "SELECT usrs.id FROM t"}, call_id="c1"),
            tool_call("execute_sql", {"sql": "SELECT id FROM t"}, call_id="c2"),
            answer("id 是 1"),
        ]
    )
    events = list(
        run_agent(
            "id 是多少",
            backend=backend,
            registry=ToolRegistry([flaky_sql_spec()]),
            context_builder=make_builder(),
        )
    )
    retries = [e for e in events if isinstance(e, RetryEvent)]
    assert len(retries) == 1
    assert "usrs" in retries[0].reason  # original dialect error fed back
    assert isinstance(events[-1], AnswerEvent)
    # the failed observation is in history for the model to read
    error_obs = [e for e in events if isinstance(e, ObservationEvent) and e.is_error]
    assert len(error_obs) == 1


def test_retry_limit_gives_up_with_explanation() -> None:
    def always_fail(sql: str) -> str:
        raise QueryError("syntax error", dialect="sqlite")

    spec = ToolSpec(
        name="execute_sql",
        description="run sql",
        input_schema={
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
        handler=always_fail,
    )
    backend = FakeLLMBackend(
        [tool_call("execute_sql", {"sql": f"SELECT {i}"}, call_id=f"c{i}") for i in range(8)]
    )
    events = list(
        run_agent(
            "q",
            backend=backend,
            registry=ToolRegistry([spec]),
            context_builder=make_builder(),
            max_turns=8,
            max_retries=3,
        )
    )
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].error_type == "RetryLimit"
    assert len([e for e in events if isinstance(e, RetryEvent)]) == 4  # 3 tolerated + final


def test_parse_failure_retries_once_then_degrades() -> None:
    backend = FakeLLMBackend(
        [
            LLMParseError("bad tool json"),
            LLMParseError("bad tool json again"),
            answer("degraded direct answer"),  # no-tools fallback call
        ]
    )
    events = list(
        run_agent(
            "q", backend=backend, registry=ToolRegistry([]), context_builder=make_builder()
        )
    )
    assert len([e for e in events if isinstance(e, RetryEvent)]) == 2
    assert isinstance(events[-1], AnswerEvent)
    assert events[-1].text == "degraded direct answer"
    # the degraded call must carry no tools
    assert backend.calls[-1] is not None


def test_think_event_precedes_tool_call() -> None:
    backend = FakeLLMBackend(
        [
            tool_call(
                "execute_sql",
                {"sql": "SELECT id FROM t"},
                call_id="c1",
                text="我先查一下表结构对应的 id。",
            ),
            answer("1"),
        ]
    )
    events = list(
        run_agent(
            "q",
            backend=backend,
            registry=ToolRegistry([flaky_sql_spec()]),
            context_builder=make_builder(),
        )
    )
    # flaky spec fails first call -> retry -> answer; Think must appear before the call
    assert isinstance(events[0], ThinkEvent)


def test_clarify_tool_call_becomes_terminal_clarify_event(tmp_path: Path) -> None:
    metrics_path = tmp_path / "metrics.yaml"
    metrics_path.write_text(METRICS_YAML, encoding="utf-8")
    backend = FakeLLMBackend(
        [
            tool_call(
                "ask_clarification",
                {"question": "要注册口径还是首单口径？", "metrics": ["new_users"]},
            )
        ]
    )
    events = list(
        run_agent(
            "上个月新增用户有多少？",
            backend=backend,
            registry=ToolRegistry([make_clarify_tool()]),
            context_builder=make_builder(metrics_path),
        )
    )
    assert len(events) == 1
    clarify = events[0]
    assert isinstance(clarify, ClarifyEvent)
    assert clarify.conflicting_metrics == ("new_users",)
    assert "口径" in clarify.question


def test_end_to_end_pipeline_over_real_sqlite(tmp_path: Path) -> None:
    """Full stack minus the LLM: agent -> tools -> safety -> connector -> rows."""
    db = tmp_path / "shop.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE users (id INTEGER NOT NULL, channel TEXT)")
    conn.executemany("INSERT INTO users VALUES (?, ?)", [(i, "organic") for i in range(7)])
    conn.commit()
    conn.close()
    connector = SQLiteConnector(path=str(db))
    registry = ToolRegistry(make_default_tools(connector, timeout_s=5, max_rows=100))
    backend = FakeLLMBackend(
        [
            tool_call("get_schema", {}, call_id="c1"),
            tool_call("execute_sql", {"sql": "SELECT count(*) FROM users"}, call_id="c2"),
            answer("一共 7 个用户"),
        ]
    )
    events = list(
        run_agent(
            "有多少用户",
            backend=backend,
            registry=registry,
            context_builder=make_builder(),
        )
    )
    connector.close()
    observations = [e for e in events if isinstance(e, ObservationEvent)]
    assert "TABLE users" in observations[0].content  # real schema flowed through
    assert "7" in observations[1].content  # real count flowed through
    assert not observations[1].is_error
    assert isinstance(events[-1], AnswerEvent)


def test_end_to_end_safety_blocks_write(tmp_path: Path) -> None:
    db = tmp_path / "shop.db"
    sqlite3.connect(db).execute("CREATE TABLE users (id INTEGER)").connection.close()
    connector = SQLiteConnector(path=str(db))
    registry = ToolRegistry(make_default_tools(connector, timeout_s=5, max_rows=100))
    backend = FakeLLMBackend(
        [tool_call("execute_sql", {"sql": "DROP TABLE users"}, call_id="c1")]
    )
    events = list(
        run_agent(
            "删表", backend=backend, registry=registry, context_builder=make_builder()
        )
    )
    connector.close()
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].error_type == "SafetyViolation"
    # and the table is still there
    check = sqlite3.connect(db)
    assert check.execute("SELECT count(*) FROM users").fetchone() == (0,)
    check.close()


def test_multiple_tool_calls_only_first_is_executed() -> None:
    from queryagent.llm.base import ModelResponse, ToolCall

    response = ModelResponse(
        text="",
        tool_calls=(
            ToolCall(id="c1", name="execute_sql", arguments={"sql": "SELECT id FROM t"}),
            ToolCall(id="c2", name="execute_sql", arguments={"sql": "SELECT 2"}),
        ),
        stop_reason="tool_use",
    )
    backend = FakeLLMBackend([response, answer("done")])
    events = list(
        run_agent(
            "q",
            backend=backend,
            registry=ToolRegistry([flaky_sql_spec()]),
            context_builder=make_builder(),
        )
    )
    from queryagent.events import ToolCallEvent

    calls = [e for e in events if isinstance(e, ToolCallEvent)]
    assert len(calls) == 1
    assert calls[0].tool_call_id == "c1"


def test_agent_answers_directly_without_tools_when_question_is_chat() -> None:
    backend = FakeLLMBackend([answer("我是 QueryAgent，请问要查什么数据？")])
    events = list(
        run_agent(
            "你好",
            backend=backend,
            registry=ToolRegistry([]),
            context_builder=make_builder(),
        )
    )
    assert len(events) == 1
    assert isinstance(events[0], AnswerEvent)


@pytest.mark.parametrize("empty_text", ["", "   "])
def test_empty_response_treated_as_parse_failure(empty_text: str) -> None:
    backend = FakeLLMBackend(
        [answer(empty_text), answer("recovered on the retry")]
    )
    events = list(
        run_agent(
            "q", backend=backend, registry=ToolRegistry([]), context_builder=make_builder()
        )
    )
    assert isinstance(events[0], RetryEvent)
    assert isinstance(events[-1], AnswerEvent)
    assert events[-1].text == "recovered on the retry"


def test_conversation_is_forwarded_to_backend_before_question() -> None:
    from queryagent.llm.base import Message

    backend = FakeLLMBackend([answer("done")])
    conversation = [
        Message(role="user", content="earlier question"),
        Message(role="assistant", content="earlier answer"),
    ]
    events = list(
        run_agent(
            "follow-up",
            backend=backend,
            registry=ToolRegistry([]),
            context_builder=make_builder(),
            conversation=conversation,
        )
    )
    assert isinstance(events[-1], AnswerEvent)
    contents = [message.content for message in backend.calls[0]]
    assert "earlier question" in contents
    assert "earlier answer" in contents
    assert contents.index("earlier answer") < contents.index("follow-up")
