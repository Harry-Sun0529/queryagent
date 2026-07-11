"""LLM backend abstraction (spec §二).

``agent.py`` only ever sees these types. Provider tool-call format differences
(Anthropic content blocks vs OpenAI tool_calls arrays) are absorbed inside
each backend — that asymmetry is the primary reason this abstraction exists.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from queryagent.tools import ToolSpec


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    """One conversation message, provider-agnostic.

    Attributes:
        role: One of "system" | "user" | "assistant" | "tool".
        content: Text content (observation text for role="tool").
        tool_calls: Set on assistant messages that requested tool use.
        tool_call_id: Set on role="tool" messages, pairing the observation
            with the assistant's originating ToolCall.
    """

    role: str
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    """Normalised model output; raw provider structures never leave a backend."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    stop_reason: str = ""


class LLMBackend(Protocol):
    """Contract for LLM providers.

    v0.1.0 implements ``AnthropicBackend``; v0.1.1 adds
    ``OpenAICompatibleBackend`` (configurable base_url covers
    DeepSeek/Qwen/GLM/OpenAI/vLLM/Ollama — all the same protocol).
    Only new implementations may be added; this signature never changes.
    """

    def complete(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Return the model's next message given the conversation so far."""
        ...
