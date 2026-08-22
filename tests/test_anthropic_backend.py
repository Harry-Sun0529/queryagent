"""Contract tests for the Anthropic backend.

This backend has never been exercised against the live API (no key), so
these tests pin the parts that are ours: what we send, what we make of the
reply, and what we do with a setting the SDK no longer accepts.
"""

from __future__ import annotations

from typing import Any

import pytest

from queryagent.llm.anthropic_backend import AnthropicBackend
from queryagent.llm.base import Message, ToolCall
from queryagent.tools import ToolSpec


class FakeBlock:
    def __init__(self, **fields: Any) -> None:
        self.__dict__.update(fields)


class FakeMessages:
    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.reply


class FakeClient:
    def __init__(self, reply: Any) -> None:
        self.messages = FakeMessages(reply)


def text_reply(text: str) -> Any:
    from anthropic.types import TextBlock

    return FakeBlock(
        content=[TextBlock(type="text", text=text, citations=None)],
        stop_reason="end_turn",
        model="claude-sonnet-5",
        usage=FakeBlock(input_tokens=10, output_tokens=3, cache_read_input_tokens=4),
    )


def make_backend(
    monkeypatch: pytest.MonkeyPatch, reply: Any, **kwargs: Any
) -> tuple[AnthropicBackend, FakeClient]:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = FakeClient(reply)
    return AnthropicBackend("claude-sonnet-5", client=client, **kwargs), client


def test_text_answer_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    backend, _client = make_backend(monkeypatch, text_reply("你好"))
    response = backend.complete([Message(role="user", content="hi")])
    assert response.text == "你好"
    assert response.usage is not None
    assert response.usage.input_tokens == 10
    assert response.usage.cached_input_tokens == 4
    assert response.usage.model == "claude-sonnet-5"


def test_temperature_is_not_sent_to_an_sdk_that_dropped_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # anthropic 1.x removed temperature from Messages.create. Sending it
    # anyway breaks type checking; ignoring it in silence would let an eval
    # believe it ran deterministically when it did not.
    backend, client = make_backend(monkeypatch, text_reply("ok"), temperature=0)
    backend.complete([Message(role="user", content="q")])
    assert "temperature" not in client.messages.calls[0]
    assert "temperature" in capsys.readouterr().err.lower()


def test_no_warning_when_temperature_is_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    make_backend(monkeypatch, text_reply("ok"))
    assert capsys.readouterr().err == ""


def test_tool_use_block_becomes_a_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from anthropic.types import ToolUseBlock

    reply = FakeBlock(
        content=[ToolUseBlock(type="tool_use", id="tu_1", name="execute_sql",
                              input={"sql": "SELECT 1"})],
        stop_reason="tool_use",
        model="claude-sonnet-5",
        usage=FakeBlock(input_tokens=1, output_tokens=1),
    )
    backend, _client = make_backend(monkeypatch, reply)
    response = backend.complete([Message(role="user", content="q")])
    assert response.tool_calls == (
        ToolCall(id="tu_1", name="execute_sql", arguments={"sql": "SELECT 1"}),
    )


def test_tool_results_are_sent_as_user_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    # Anthropic has no "tool" role: a result is a user message carrying a
    # tool_result block paired by id. Getting this wrong is an API error.
    backend, client = make_backend(monkeypatch, text_reply("ok"))
    tool = ToolSpec(
        name="execute_sql",
        description="run sql",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: "",
    )
    backend.complete(
        [
            Message(role="system", content="be careful"),
            Message(role="user", content="q"),
            Message(
                role="assistant",
                content="thinking",
                tool_calls=(ToolCall(id="tu_1", name="execute_sql", arguments={}),),
            ),
            Message(role="tool", content="42 rows", tool_call_id="tu_1"),
        ],
        tools=[tool],
    )
    sent = client.messages.calls[0]
    assert sent["system"] == "be careful"  # system is hoisted out of messages
    assert [m["role"] for m in sent["messages"]] == ["user", "assistant", "user"]
    result_block = sent["messages"][2]["content"][0]
    assert result_block["type"] == "tool_result"
    assert result_block["tool_use_id"] == "tu_1"
