"""Unit tests for the OpenAI-compatible backend (httpx MockTransport, no network)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from queryagent.errors import LLMParseError
from queryagent.llm.base import Message, ToolCall
from queryagent.llm.openai_backend import OpenAICompatibleBackend
from queryagent.tools import ToolSpec


def make_backend(
    monkeypatch: pytest.MonkeyPatch,
    reply: dict[str, Any] | None = None,
    status_code: int = 200,
    captured: list[dict[str, Any]] | None = None,
) -> OpenAICompatibleBackend:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured.append(json.loads(request.content))
        return httpx.Response(status_code, json=reply or {})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleBackend(
        "deepseek-chat", base_url="https://api.example.com/v1", client=client
    )


def text_reply(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}


def test_text_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, text_reply("你好"))
    response = backend.complete([Message(role="user", content="hi")])
    assert response.text == "你好"
    assert response.tool_calls == ()
    assert response.stop_reason == "stop"


def test_tool_call_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_9",
                            "type": "function",
                            "function": {
                                "name": "execute_sql",
                                "arguments": '{"sql": "SELECT 1"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    backend = make_backend(monkeypatch, reply)
    response = backend.complete([Message(role="user", content="q")])
    assert response.text == ""
    assert response.tool_calls == (
        ToolCall(id="call_9", name="execute_sql", arguments={"sql": "SELECT 1"}),
    )


def test_request_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    backend = make_backend(monkeypatch, text_reply("ok"), captured=captured)
    messages = [
        Message(role="system", content="be careful"),
        Message(role="user", content="q"),
        Message(
            role="assistant",
            content="thinking",
            tool_calls=(ToolCall(id="c1", name="execute_sql", arguments={"sql": "SELECT 1"}),),
        ),
        Message(role="tool", content="1", tool_call_id="c1"),
    ]
    tools = [
        ToolSpec(
            name="execute_sql",
            description="run sql",
            input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
            handler=lambda sql: sql,
        )
    ]
    backend.complete(messages, tools=tools)
    body = captured[0]
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["system", "user", "assistant", "tool"]
    assistant = body["messages"][2]
    assert assistant["tool_calls"][0]["function"]["name"] == "execute_sql"
    # OpenAI protocol carries arguments as a JSON *string*
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {"sql": "SELECT 1"}
    assert body["messages"][3]["tool_call_id"] == "c1"
    assert body["tools"][0]["function"]["name"] == "execute_sql"


def test_malformed_tool_arguments_raise_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "c1", "function": {"name": "t", "arguments": "not json"}}
                    ]
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    backend = make_backend(monkeypatch, reply)
    with pytest.raises(LLMParseError):
        backend.complete([Message(role="user", content="q")])


def test_http_error_surfaces_status_and_body(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = make_backend(monkeypatch, {"error": "bad key"}, status_code=401)
    with pytest.raises(RuntimeError, match="401"):
        backend.complete([Message(role="user", content="q")])


def test_missing_api_key_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAICompatibleBackend("m", base_url="https://api.example.com")


def flaky_backend(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[httpx.Response | Exception],
    calls: list[int],
) -> OpenAICompatibleBackend:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleBackend(
        "m", base_url="https://api.example.com", client=client, retry_backoff_s=0
    )


def test_retries_on_http_500_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    backend = flaky_backend(
        monkeypatch,
        [httpx.Response(500, text="boom"), httpx.Response(200, json=text_reply("ok"))],
        calls,
    )
    response = backend.complete([Message(role="user", content="q")])
    assert response.text == "ok"
    assert len(calls) == 2


def test_retries_on_transport_error_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    backend = flaky_backend(
        monkeypatch,
        [httpx.ConnectError("reset"), httpx.Response(200, json=text_reply("ok"))],
        calls,
    )
    assert backend.complete([Message(role="user", content="q")]).text == "ok"
    assert len(calls) == 2


def test_persistent_500_fails_after_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    backend = flaky_backend(
        monkeypatch, [httpx.Response(500, text="boom") for _ in range(5)], calls
    )
    with pytest.raises(RuntimeError, match="500"):
        backend.complete([Message(role="user", content="q")])
    assert len(calls) == 3  # initial + 2 retries


def test_429_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    backend = flaky_backend(
        monkeypatch,
        [httpx.Response(429, text="slow down"), httpx.Response(200, json=text_reply("ok"))],
        calls,
    )
    assert backend.complete([Message(role="user", content="q")]).text == "ok"
    assert len(calls) == 2


def test_plain_4xx_fails_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    backend = flaky_backend(monkeypatch, [httpx.Response(401, text="bad key")], calls)
    with pytest.raises(RuntimeError, match="401"):
        backend.complete([Message(role="user", content="q")])
    assert len(calls) == 1  # a bad key does not get better by retrying


def test_temperature_forwarded_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=text_reply("ok"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OpenAICompatibleBackend(
        "m", base_url="https://api.example.com", temperature=0.0, client=client
    )
    backend.complete([Message(role="user", content="q")])
    assert captured[0]["temperature"] == 0.0

    captured.clear()
    default_backend = make_backend(monkeypatch, text_reply("ok"), captured=captured)
    default_backend.complete([Message(role="user", content="q")])
    assert "temperature" not in captured[0]  # provider default when unset


def test_usage_parsed_with_cache_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {
        "model": "deepseek-v4-flash",
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 80,
            "prompt_cache_hit_tokens": 1024,
            "prompt_cache_miss_tokens": 176,
        },
    }
    backend = make_backend(monkeypatch, reply)
    usage = backend.complete([Message(role="user", content="q")]).usage
    assert usage is not None
    assert usage.input_tokens == 1200
    assert usage.output_tokens == 80
    assert usage.cached_input_tokens == 1024
    assert usage.model == "deepseek-v4-flash"


def test_usage_absent_degrades_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # Not every OpenAI-compatible server returns usage; must not crash.
    backend = make_backend(monkeypatch, text_reply("ok"))
    assert backend.complete([Message(role="user", content="q")]).usage is None


def test_usage_without_cache_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {
        "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }
    usage = make_backend(monkeypatch, reply).complete(
        [Message(role="user", content="q")]
    ).usage
    assert usage is not None
    assert usage.cached_input_tokens == 0


def test_reasoning_content_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {
        "choices": [
            {
                "message": {
                    "content": "I'll check the schema.",
                    "reasoning_content": "The user asks about tables; use get_schema.",
                },
                "finish_reason": "stop",
            }
        ]
    }
    response = make_backend(monkeypatch, reply).complete([Message(role="user", content="q")])
    assert response.reasoning.startswith("The user asks")
    assert response.text == "I'll check the schema."


def test_reasoning_is_sent_back_on_assistant_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # DeepSeek thinking models reject turn 2 unless reasoning_content is echoed.
    captured: list[dict[str, Any]] = []
    backend = make_backend(monkeypatch, text_reply("ok"), captured=captured)
    backend.complete(
        [
            Message(role="user", content="q"),
            Message(
                role="assistant",
                content="thinking out loud",
                reasoning="internal chain",
                tool_calls=(ToolCall(id="c1", name="get_schema", arguments={}),),
            ),
            Message(role="tool", content="schema", tool_call_id="c1"),
        ]
    )
    assistant = captured[0]["messages"][1]
    assert assistant["reasoning_content"] == "internal chain"


def test_no_reasoning_field_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    backend = make_backend(monkeypatch, text_reply("ok"), captured=captured)
    backend.complete(
        [Message(role="assistant", content="plain", tool_calls=(
            ToolCall(id="c1", name="t", arguments={}),))]
    )
    assert "reasoning_content" not in captured[0]["messages"][0]


def test_tool_calls_without_ids_get_usable_distinct_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # vLLM and some Ollama builds omit the id. An empty id breaks the
    # tool_call/tool_result pairing both providers require, and collapses
    # two calls into one when the eval runner pairs observations by id.
    reply = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"function": {"name": "get_schema", "arguments": "{}"}},
                        {"function": {"name": "execute_sql",
                                      "arguments": '{"sql": "SELECT 1"}'}},
                    ]
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    calls = make_backend(monkeypatch, reply).complete(
        [Message(role="user", content="q")]
    ).tool_calls
    assert all(c.id for c in calls)
    assert len({c.id for c in calls}) == 2
