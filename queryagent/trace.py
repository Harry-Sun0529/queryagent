"""Trace persistence: write the agent event stream to JSONL and read it back.

The event stream is already the project's single output seam, so persistence
is just one more consumer — nothing in ``agent.py`` changes to support it.
A saved trace answers "what did the agent actually do" after the fact, which
is the only practical way to debug a non-deterministic system.

Privacy: a trace records the question, the SQL and the observations, which
for a real database means business data on disk. Traces are written under
``.queryagent/traces/`` (gitignored), the CLI announces the first write, and
``--no-trace`` / ``trace: false`` turn it off.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    RetryEvent,
    ThinkEvent,
    ToolCallEvent,
    UsageEvent,
)

TRACE_DIR_NAME = ".queryagent/traces"
DEFAULT_KEEP = 50

_EVENT_TYPES: dict[str, type[AgentEvent]] = {
    cls.__name__: cls
    for cls in (
        ThinkEvent,
        ToolCallEvent,
        ObservationEvent,
        AnswerEvent,
        ErrorEvent,
        RetryEvent,
        ClarifyEvent,
        UsageEvent,
    )
}

_SLUG_STRIP = re.compile(r"[^\w一-鿿-]+")


def event_to_dict(event: AgentEvent) -> dict[str, Any]:
    """Serialise one event, tagging it with its class name."""
    return {"type": type(event).__name__, **dataclasses.asdict(event)}


def event_from_dict(data: Mapping[str, Any]) -> AgentEvent:
    """Rebuild an event from its serialised form.

    Fields absent from the payload fall back to their dataclass defaults, so
    traces stay readable across versions that add optional fields. JSON has
    no tuples, so list values are restored to tuples where the field declares
    one.

    Raises:
        ValueError: If the ``type`` tag names no known event.
    """
    payload = dict(data)
    name = str(payload.pop("type", ""))
    event_type = _EVENT_TYPES.get(name)
    if event_type is None:
        raise ValueError(f"unknown event type in trace: {name!r}")
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(event_type):
        if field.name not in payload:
            continue
        value = payload[field.name]
        if isinstance(value, list) and "tuple" in str(field.type):
            value = tuple(value)
        kwargs[field.name] = value
    return event_type(**kwargs)


class TraceWriter:
    """Append events to a JSONL file, creating it on the first write."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: TextIO | None = None

    def write(self, event: AgentEvent) -> None:
        """Append one event; opens the file (and its parents) on first use."""
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("w", encoding="utf-8")
        json.dump(event_to_dict(event), self._handle, ensure_ascii=False)
        self._handle.write("\n")
        self._handle.flush()  # a crashed run is exactly when the trace matters

    def close(self) -> None:
        """Close the file if anything was written."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    @property
    def started(self) -> bool:
        """True once at least one event has been written."""
        return self._handle is not None


def read_trace(path: str | Path) -> list[AgentEvent]:
    """Read a JSONL trace back into events, skipping blank lines."""
    events: list[AgentEvent] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(event_from_dict(json.loads(line)))
    return events


def new_trace_path(directory: str | Path, question: str) -> Path:
    """Build a sortable, filesystem-safe trace filename for one question.

    The timestamp has second resolution, so asking the same question twice
    within a second would otherwise reuse the name and overwrite the earlier
    trace; a numeric suffix is appended until the name is free.
    """
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    slug = _SLUG_STRIP.sub("-", question.strip())[:40].strip("-")
    stem = f"{stamp}-{slug}" if slug else stamp
    directory = Path(directory)
    candidate = directory / f"{stem}.jsonl"
    suffix = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{suffix}.jsonl"
        suffix += 1
    return candidate


def prune_traces(directory: str | Path, keep: int = DEFAULT_KEEP, reserve: int = 0) -> None:
    """Delete all but the ``keep`` newest traces; ignores non-trace files.

    Args:
        directory: Where traces live.
        keep: How many traces may remain afterwards.
        reserve: Slots to leave free for traces about to be written, so the
            cap holds once they land rather than being exceeded by one.
    """
    files = sorted(Path(directory).glob("*.jsonl"))
    excess = len(files) - max(keep - reserve, 0)
    for path in files[: max(excess, 0)]:
        path.unlink(missing_ok=True)
