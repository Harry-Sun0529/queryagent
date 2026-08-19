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
        reasoning: Provider-side chain of thought for assistant messages.
            Reasoning models (DeepSeek v4 thinking mode) reject a follow-up
            turn unless the previous turn's reasoning is sent back unchanged.
    """

    role: str
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    reasoning: str = ""  # thinking models require this echoed back verbatim


@dataclass(frozen=True)
class Usage:
    """Token accounting for one model call, normalised across providers.

    ``cached_input_tokens`` is the subset of ``input_tokens`` served from the
    provider's prompt cache — it matters because cached input is roughly 30x
    cheaper on DeepSeek, and this agent re-sends a stable system prompt
    (schema + metrics) on every turn.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    model: str = ""


@dataclass(frozen=True)
class ModelResponse:
    """Normalised model output; raw provider structures never leave a backend."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    stop_reason: str = ""
    usage: Usage | None = None  # None when the provider reports no usage
    reasoning: str = ""  # thinking-model chain of thought, echoed back next turn


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
