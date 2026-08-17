"""Unit tests for the context builder: assembly, metrics injection, trimming."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from queryagent.context import ContextBuilder, estimate_tokens
from queryagent.llm.base import Message
from queryagent.metrics.yaml_store import YamlMetricStore

METRICS_YAML = """\
metrics:
  - name: new_users
    display_name: 新增用户
    aliases: [新用户, 新增]
    definition: 按 users.created_at 日期计数。
    caution: 运营口径按 first_order_at 计数。
  - name: aov
    display_name: 客单价
    definition: paid 订单 amount 均值。
"""


def make_builder() -> ContextBuilder:
    return ContextBuilder(
        schema_text="TABLE users\n  id BIGINT NOT NULL",
        dialect="mysql",
        current_date=date(2026, 7, 11),
    )


def test_system_prompt_contains_dialect_schema_and_date() -> None:
    messages = make_builder().build("上个月每天的新增用户数", history=[])
    system = messages[0]
    assert system.role == "system"
    assert "mysql" in system.content
    assert "TABLE users" in system.content
    assert "2026-07-11" in system.content  # anchors "last month" style questions


def test_question_is_first_user_message() -> None:
    messages = make_builder().build("有多少用户?", history=[])
    assert messages[1] == Message(role="user", content="有多少用户?")
    assert len(messages) == 2


def test_history_is_appended_untrimmed() -> None:
    history = [
        Message(role="assistant", content="thinking..."),
        Message(role="tool", content="42", tool_call_id="c1"),
    ]
    messages = make_builder().build("有多少用户?", history=history)
    assert messages[2:] == history


def test_estimate_tokens_is_positive_and_monotonic() -> None:
    assert estimate_tokens("") >= 1
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)


def make_metric_builder(tmp_path: Path) -> ContextBuilder:
    path = tmp_path / "metrics.yaml"
    path.write_text(METRICS_YAML, encoding="utf-8")
    return ContextBuilder(
        schema_text="TABLE users\n  id BIGINT NOT NULL",
        dialect="sqlite",
        metric_store=YamlMetricStore(path),
    )


def test_matched_metric_injected_with_caution_guidance(tmp_path: Path) -> None:
    messages = make_metric_builder(tmp_path).build("上个月新增用户有多少?", history=[])
    system = messages[0].content
    assert "new_users" in system
    assert "按 users.created_at 日期计数" in system
    assert "运营口径" in system  # caution text
    assert "ask_clarification" in system  # clarify decision rule present


def test_unmatched_question_gets_no_metrics_section(tmp_path: Path) -> None:
    messages = make_metric_builder(tmp_path).build("数据库里有哪些表?", history=[])
    system = messages[0].content
    assert "new_users" not in system
    assert "ask_clarification" not in system


def test_metric_without_caution_gets_no_clarify_guidance(tmp_path: Path) -> None:
    messages = make_metric_builder(tmp_path).build("客单价是多少?", history=[])
    system = messages[0].content
    assert "aov" in system
    assert "ask_clarification" not in system


def test_budget_trims_oldest_history_in_pairs() -> None:
    builder = ContextBuilder(
        schema_text="TABLE t\n  id INT", dialect="sqlite", token_budget=400
    )
    history = []
    for i in range(6):
        history.append(Message(role="assistant", content=f"thinking {i} " + "x" * 200))
        history.append(Message(role="tool", content=f"obs {i} " + "y" * 200, tool_call_id=f"c{i}"))
    messages = builder.build("q", history=history)
    assert messages[0].role == "system"  # never trimmed
    assert messages[1].role == "user"  # never trimmed
    # whatever survives must not start with an orphaned tool message
    if len(messages) > 2:
        assert messages[2].role == "assistant"
    # newest history survives, oldest is gone
    contents = " ".join(m.content for m in messages[2:])
    assert "thinking 0" not in contents
    assert len(messages) < 2 + len(history)


def test_budget_generous_enough_keeps_everything() -> None:
    builder = ContextBuilder(schema_text="TABLE t\n  id INT", dialect="sqlite")
    history = [
        Message(role="assistant", content="a"),
        Message(role="tool", content="b", tool_call_id="c1"),
    ]
    assert len(builder.build("q", history=history)) == 4
