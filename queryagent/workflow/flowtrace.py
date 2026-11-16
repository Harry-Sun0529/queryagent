"""A trace of the confirmed flow: how a number came about, step by step.

The state file keeps outcomes — the draft, who confirmed which version, what
ran. It does not keep the way there: what retrieval returned, which rules the
extractor proposed and which were dropped and why, whether an earlier choice
was offered, what was refused and at which step. When a number is disputed
that is what gets asked for, and until 1.1 it was nowhere.

Three decisions shape this module (ADR-016):

- **Events come from where the decision is made** — the service and the
  builders — never from a door. The terminal, the page and MCP therefore
  cannot disagree about what happened, for the reason the workspace check
  moved into the service in 1.0.1.
- **A builder does not know the draft it is building for**, so it says what
  it did with ``note()`` and the service, which does know, binds the draft
  around the call. Outside a binding ``note()`` does nothing.
- **A trace holds only what the acting identity could already see.** No
  document text beyond the rules on that identity's own sheet, no result
  rows. Each event names its workspace, and the scenario leak gate reads
  them by it.

A trace is an aid, not a record: it can be switched off, it is pruned, and
anyone on the machine can edit it. Who confirmed what lives in the state
file. And a trace that cannot be written never fails the flow.
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import os
import sys
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

FLOW_DIR_NAME = "flows"
KEEP_FLOW_TRACES = 200
EVENT_TYPE = "FlowEvent"

PREPARED = "prepared"
RETRIEVED = "retrieved"
EXTRACTED = "extracted"
JUDGED = "judged"
HISTORY = "history"
AMENDED = "amended"
CONFIRMED = "confirmed"
REFUSED = "refused"
ADMITTED = "admitted"
EXECUTED = "executed"


@dataclass(frozen=True)
class FlowEvent:
    """One step of one draft's way to a number."""

    kind: str
    draft_id: str
    at: str
    subject: str
    workspace: str
    channel: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": EVENT_TYPE,
            "kind": self.kind,
            "draft_id": self.draft_id,
            "at": self.at,
            "subject": self.subject,
            "workspace": self.workspace,
            "channel": self.channel,
            "detail": dict(self.detail),
        }


Emit = Callable[[FlowEvent], None]


def silent(_event: FlowEvent) -> None:
    """The emitter of a workflow nobody is tracing."""


# ------------------------------------------------------- notes from builders

_bound: contextvars.ContextVar[Callable[[str, Mapping[str, Any]], None] | None] = (
    contextvars.ContextVar("queryagent_flow_note", default=None)
)


def note(kind: str, **detail: Any) -> None:
    """Say what a builder just did, for whichever draft is being prepared.

    A no-op unless the service has bound a draft around this call, so a
    builder used on its own — in a test, by an embedder — needs nothing.
    """
    bound = _bound.get()
    if bound is not None:
        bound(kind, detail)


@contextlib.contextmanager
def binding(record: Callable[[str, Mapping[str, Any]], None]) -> Iterator[None]:
    """Route ``note()`` calls made inside the block to ``record``."""
    token = _bound.set(record)
    try:
        yield
    finally:
        _bound.reset(token)


# ------------------------------------------------------------------ writing


_announced = False


class FlowTraceWriter:
    """Appends each event to its draft's file, one line per event.

    One file per draft and workspace, ``flows/<draft>-<workspace>.jsonl``, so
    the steps of a draft prepared by an MCP server, confirmed on the page and
    run by the server again land together though three processes wrote them.
    Each line is written with a single ``O_APPEND`` write, which is what
    keeps those processes from cutting into each other's lines.
    """

    def __init__(
        self, directory: str | Path, *, warn: Callable[[str], None] | None = None
    ) -> None:
        self.directory = Path(directory) / FLOW_DIR_NAME
        self._warn = warn or (lambda text: print(text, file=sys.stderr))
        self._failed = False
        self._pruned = False

    def path_of(self, draft_id: str, workspace: str) -> Path:
        return self.directory / f"{_safe(draft_id)}-{_safe(workspace)}.jsonl"

    def write(self, event: FlowEvent) -> None:
        """Append one event. Never raises: a trace must not be why a flow failed."""
        try:
            line = json.dumps(event.to_dict(), ensure_ascii=False, default=str) + "\n"
            self.directory.mkdir(parents=True, exist_ok=True)
            target = self.path_of(event.draft_id, event.workspace)
            if not self._pruned:
                # Once per writer, before its first line. Found in the 1.1
                # read-through: this ran only when the folder was new, which
                # is when there is nothing to prune, so traces only ever grew.
                self._pruned = True
                prune_flow_traces(
                    self.directory, KEEP_FLOW_TRACES, reserve=0 if target.exists() else 1
                )
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_APPEND | os.O_CREAT,
                0o600,
            )
            try:
                os.write(descriptor, line.encode("utf-8"))
            finally:
                os.close(descriptor)
        except Exception as exc:  # noqa: BLE001 - observation only, by design
            if not self._failed:
                self._failed = True
                self._warn(
                    f"[trace] 无法写入确认流记录（{type(exc).__name__}: {exc}）；流程照常继续。"
                )
            return
        global _announced
        if not _announced:
            # Once per process (ADR-005), however many workflows it assembles.
            _announced = True
            self._warn(
                f"[trace] 确认流的过程已记录到 {self.directory.resolve()}/ —— 含问题、口径规则、"
                "SQL 与参数，不含查询结果行与文档正文。关闭方式：config 里 trace: false"
            )


def _safe(text: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in text)[:64]


def prune_flow_traces(directory: Path, keep: int = KEEP_FLOW_TRACES, reserve: int = 0) -> None:
    """Keep the ``keep`` most recently written draft traces."""
    files = sorted(directory.glob("*.jsonl"), key=lambda path: path.stat().st_mtime)
    for path in files[: max(len(files) - max(keep - reserve, 0), 0)]:
        path.unlink(missing_ok=True)


# ------------------------------------------------------------------ reading


def is_flow_trace(path: str | Path) -> bool:
    """Whether the file's first readable line is a flow event."""
    for line in Path(path).read_bytes().splitlines():
        if not line.strip():
            continue
        try:
            return bool(json.loads(line).get("type") == EVENT_TYPE)
        except (json.JSONDecodeError, AttributeError):
            return False
    return False


def read_flow_trace(path: str | Path) -> list[FlowEvent]:
    """The events in a draft's trace, skipping lines that cannot be read.

    A process killed mid-write leaves a partial last line; that costs the
    line, never the file.
    """
    events: list[FlowEvent] = []
    for line in Path(path).read_bytes().splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if raw.get("type") != EVENT_TYPE:
                continue
            events.append(
                FlowEvent(
                    kind=str(raw["kind"]),
                    draft_id=str(raw["draft_id"]),
                    at=str(raw["at"]),
                    subject=str(raw["subject"]),
                    workspace=str(raw["workspace"]),
                    channel=str(raw["channel"]),
                    detail=dict(raw.get("detail") or {}),
                )
            )
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            continue
    return events


# ---------------------------------------------------------------- rendering

_TITLES = {
    PREPARED: "准备草案",
    RETRIEVED: "检索文档",
    EXTRACTED: "抽取规则",
    JUDGED: "评审转述",
    HISTORY: "历史选择",
    AMENDED: "补充口径",
    CONFIRMED: "确认",
    REFUSED: "✗ 拒绝",
    ADMITTED: "准入",
    EXECUTED: "执行",
}


def render_flow(events: list[FlowEvent]) -> list[str]:
    """A draft's trace as lines a person who was not there can follow."""
    if not events:
        return ["（这份记录里没有可读的事件）"]
    first = events[0]
    lines = [f"确认流记录  草案 #{first.draft_id[:8]}  {first.subject}@{first.workspace}", ""]
    for event in events:
        when = _clock(event.at)
        lines.append(f"{when}  [{event.channel}]  {_TITLES.get(event.kind, event.kind)}")
        lines.extend(f"    {text}" for text in _detail_lines(event))
    return lines


def _clock(stamp: str) -> str:
    try:
        return datetime.fromisoformat(stamp).strftime("%m-%d %H:%M:%S")
    except ValueError:
        return stamp


def _detail_lines(event: FlowEvent) -> list[str]:
    detail = event.detail
    if event.kind == EXTRACTED:
        lines = [
            f"采纳 {rule.get('key')}：{rule.get('value')}  ← {rule.get('ref')}"
            for rule in detail.get("adopted", [])
        ]
        lines.extend(
            f"✗ 丢弃 {dropped.get('key') or '（无键）'}：{dropped.get('reason')}"
            for dropped in detail.get("dropped", [])
        )
        return lines or ["模型没有提出任何规则"]
    if event.kind == RETRIEVED:
        hits = detail.get("hits", [])
        if not hits:
            return ["没有检索到该身份可见的相关片段"]
        return [f"{hit.get('ref')}  得分 {hit.get('score')}" for hit in hits]
    lines = []
    for key, value in detail.items():
        if value in ("", None, [], {}):
            continue
        if isinstance(value, list) and any(len(str(item)) > 30 for item in value):
            lines.append(f"{key}：")
            lines.extend(f"  · {item}" for item in value)
            continue
        shown = "、".join(str(item) for item in value) if isinstance(value, list) else value
        lines.append(f"{key}：{shown}")
    return lines
