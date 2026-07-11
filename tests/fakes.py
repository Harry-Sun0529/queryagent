"""Test doubles (AI-OWNED, spec §〇): a scripted LLM backend."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from queryagent.llm.base import Message, ModelResponse, ToolCall
from queryagent.tools import ToolSpec


class FakeLLMBackend:
    """LLMBackend that replays a scripted list of responses in order.

    Records every ``complete`` call (messages and tools) for assertions.
    Raises AssertionError when the script runs out — a test asking for more
    turns than it scripted is a test bug, not agent behaviour.
    """

    def __init__(self, responses: Sequence[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[list[Message]] = []

    def complete(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        self.calls.append(list(messages))
        if not self._responses:
            raise AssertionError("FakeLLMBackend script exhausted")
        return self._responses.pop(0)


def answer(text: str) -> ModelResponse:
    """Script entry: the model gives a final answer."""
    return ModelResponse(text=text, tool_calls=(), stop_reason="end_turn")


def tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    call_id: str = "call_1",
    text: str = "",
) -> ModelResponse:
    """Script entry: the model requests one tool call (optionally with thinking text)."""
    call = ToolCall(id=call_id, name=name, arguments=arguments)
    return ModelResponse(text=text, tool_calls=(call,), stop_reason="tool_use")
