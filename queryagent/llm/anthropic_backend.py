"""Anthropic implementation of the ``LLMBackend`` protocol.

All Anthropic-specific message/tool-call format handling lives here;
``agent.py`` never touches the SDK's raw response structures (spec §二).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, cast

from anthropic import Anthropic, omit
from anthropic.types import MessageParam, TextBlock, ToolParam, ToolUseBlock

from queryagent.llm.base import Message, ModelResponse, ToolCall
from queryagent.tools import ToolSpec


class AnthropicBackend:
    """LLMBackend over the Anthropic Messages API."""

    def __init__(self, model: str, *, max_tokens: int = 2048) -> None:
        """Create a backend; the API key is read from ``ANTHROPIC_API_KEY``.

        Raises:
            ValueError: If the environment variable is not set (keys are never
                accepted via config or arguments, spec §二).
        """
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError(
                "ANTHROPIC_API_KEY is not set; API keys are read from the environment only"
            )
        self._client = Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Call the Messages API and normalise the response to ModelResponse."""
        system, converted = _convert_messages(messages)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system if system else omit,
            messages=converted,
            tools=[_convert_tool(t) for t in tools] if tools else omit,
            **kwargs,
        )
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                arguments = cast("dict[str, Any]", block.input) or {}
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=arguments))
        return ModelResponse(
            text="".join(text_parts),
            tool_calls=tuple(tool_calls),
            stop_reason=response.stop_reason or "",
        )


def _convert_tool(spec: ToolSpec) -> ToolParam:
    return {
        "name": spec.name,
        "description": spec.description,
        "input_schema": spec.input_schema,
    }


def _convert_messages(messages: Sequence[Message]) -> tuple[str, list[MessageParam]]:
    """Split system text out and convert the rest to Anthropic message params."""
    system_parts: list[str] = []
    converted: list[MessageParam] = []
    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
        elif message.role == "user":
            converted.append({"role": "user", "content": message.content})
        elif message.role == "assistant":
            blocks: list[Any] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                blocks.append(
                    {"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments}
                )
            converted.append(cast(MessageParam, {"role": "assistant", "content": blocks}))
        elif message.role == "tool":
            converted.append(
                cast(
                    MessageParam,
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id or "",
                                "content": message.content,
                            }
                        ],
                    },
                )
            )
        else:
            raise ValueError(f"unsupported message role: {message.role}")
    return "\n\n".join(system_parts), converted
