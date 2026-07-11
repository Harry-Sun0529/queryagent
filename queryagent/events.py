"""Agent event stream (spec §二) — the project's most important seam.

``run_agent`` yields these events; every consumer (v0.1.0 demo printer,
v0.1.1 CLI, v0.2.0 eval runner, any future UI) is just a different reader of
the same stream. ``agent.py`` never renders anything itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentEvent:
    """Base class for events produced by the agent loop."""


@dataclass(frozen=True)
class ThinkEvent(AgentEvent):
    """The model's intermediate reasoning text for one turn."""

    text: str


@dataclass(frozen=True)
class ToolCallEvent(AgentEvent):
    """The agent is about to dispatch a tool call proposed by the model."""

    tool_name: str
    arguments: dict[str, Any]
    tool_call_id: str


@dataclass(frozen=True)
class ObservationEvent(AgentEvent):
    """Result of a tool call (including validation/query failures)."""

    content: str
    is_error: bool
    tool_call_id: str


@dataclass(frozen=True)
class AnswerEvent(AgentEvent):
    """The final natural-language answer; terminates the stream."""

    text: str


@dataclass(frozen=True)
class ErrorEvent(AgentEvent):
    """The loop terminated abnormally (safety violation, turn limit, ...)."""

    error_type: str
    message: str


@dataclass(frozen=True)
class RetryEvent(AgentEvent):
    """The agent is retrying after a recoverable failure (v0.1.1 self-repair)."""

    reason: str
    attempt: int


@dataclass(frozen=True)
class ClarifyEvent(AgentEvent):
    """The agent asks the user a clarifying question instead of guessing.

    Defined in v0.1.0 per spec §二; produced starting v0.2.0 when matched
    metrics carry conflicting definitions (``caution`` field) and the question
    does not disambiguate.
    """

    question: str
    conflicting_metrics: tuple[str, ...]
