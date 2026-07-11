"""OpenAI-compatible backend, hand-written over httpx (spec §三 v0.1.1).

One implementation covers DeepSeek / Qwen / GLM / OpenAI / vLLM / Ollama —
they all expose the same chat-completions protocol; only ``base_url`` and
``model`` differ. Written against httpx directly instead of the ``openai``
package to keep the dependency tree minimal (spec §四 — decision to be
recorded as an ADR by the human in v0.2.0).

Tool-call format differences vs Anthropic (function wrapper objects,
JSON-*string* arguments) are fully absorbed here; ``agent.py`` never sees
them (spec §二).
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

import httpx

from queryagent.errors import LLMParseError
from queryagent.llm.base import Message, ModelResponse, ToolCall
from queryagent.tools import ToolSpec


class OpenAICompatibleBackend:
    """LLMBackend over the OpenAI chat-completions protocol."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str,
        max_tokens: int = 2048,
        timeout_s: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        """Create a backend; the API key is read from ``OPENAI_API_KEY``.

        Args:
            model: Model name, e.g. "deepseek-chat".
            base_url: Endpoint prefix before ``/chat/completions``, e.g.
                "https://api.deepseek.com" or "https://api.openai.com/v1".
            max_tokens: Completion token cap.
            timeout_s: HTTP timeout.
            client: Injectable httpx client (tests use a MockTransport).

        Raises:
            ValueError: If ``OPENAI_API_KEY`` is not set (keys never come from
                config or arguments, spec §二).
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set; API keys are read from the environment only"
            )
        self._model = model
        self._max_tokens = max_tokens
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._client = client or httpx.Client(timeout=timeout_s)

    def complete(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Call chat/completions and normalise the response to ModelResponse."""
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [_convert_message(m) for m in messages],
            **kwargs,
        }
        if tools:
            body["tools"] = [_convert_tool(t) for t in tools]
        response = self._client.post(self._url, json=body, headers=self._headers)
        if response.status_code >= 400:
            raise RuntimeError(
                f"LLM request failed with HTTP {response.status_code}: {response.text[:500]}"
            )
        return _parse_response(response.json())

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


def _convert_tool(spec: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.input_schema,
        },
    }


def _convert_message(message: Message) -> dict[str, Any]:
    if message.role == "assistant" and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in message.tool_calls
            ],
        }
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id or "",
            "content": message.content,
        }
    if message.role in ("system", "user", "assistant"):
        return {"role": message.role, "content": message.content}
    raise ValueError(f"unsupported message role: {message.role}")


def _parse_response(data: Any) -> ModelResponse:
    try:
        choice = data["choices"][0]
        raw_message = choice["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMParseError(f"unexpected chat-completions response shape: {exc}") from exc
    tool_calls: list[ToolCall] = []
    for raw_call in raw_message.get("tool_calls") or []:
        function = raw_call.get("function") or {}
        raw_args = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            raise LLMParseError(
                f"tool call arguments are not valid JSON: {raw_args[:200]}"
            ) from exc
        if not isinstance(arguments, dict):
            raise LLMParseError(f"tool call arguments must be an object: {raw_args[:200]}")
        tool_calls.append(
            ToolCall(
                id=str(raw_call.get("id") or ""),
                name=str(function.get("name") or ""),
                arguments=arguments,
            )
        )
    return ModelResponse(
        text=raw_message.get("content") or "",
        tool_calls=tuple(tool_calls),
        stop_reason=str(choice.get("finish_reason") or ""),
    )
