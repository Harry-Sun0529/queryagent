"""Unit tests for the v0.1.0 (naive) context builder."""

from __future__ import annotations

from datetime import date

from queryagent.context import ContextBuilder, estimate_tokens
from queryagent.llm.base import Message


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
