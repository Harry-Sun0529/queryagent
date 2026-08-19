"""Unit tests for trace serialisation, writing and retention."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
from queryagent.trace import (
    TraceWriter,
    event_from_dict,
    event_to_dict,
    new_trace_path,
    prune_traces,
    read_trace,
)

ALL_EVENTS: list[AgentEvent] = [
    ThinkEvent(text="先看 schema"),
    ToolCallEvent(tool_name="execute_sql", arguments={"sql": "SELECT 1"}, tool_call_id="c1"),
    ObservationEvent(content="1\n(1 rows)", is_error=False, tool_call_id="c1"),
    RetryEvent(reason="no such column", attempt=1),
    ClarifyEvent(question="哪种口径？", conflicting_metrics=("new_users", "gmv")),
    UsageEvent(
        model="deepseek-v4-flash",
        input_tokens=1189,
        output_tokens=84,
        cached_input_tokens=256,
        latency_ms=1280,
    ),
    ErrorEvent(error_type="MaxTurns", message="no final answer"),
    AnswerEvent(text="42"),
]


@pytest.mark.parametrize("event", ALL_EVENTS, ids=lambda e: type(e).__name__)
def test_event_roundtrip(event: AgentEvent) -> None:
    restored = event_from_dict(json.loads(json.dumps(event_to_dict(event))))
    assert restored == event
    assert type(restored) is type(event)


def test_clarify_tuple_survives_json_list_coercion() -> None:
    # JSON has no tuples; without coercion back this compares unequal.
    event = ClarifyEvent(question="?", conflicting_metrics=("a", "b"))
    restored = event_from_dict(json.loads(json.dumps(event_to_dict(event))))
    assert isinstance(restored, ClarifyEvent)
    assert restored.conflicting_metrics == ("a", "b")


def test_unknown_event_type_rejected() -> None:
    with pytest.raises(ValueError, match="unknown event type"):
        event_from_dict({"type": "TeleportEvent", "x": 1})


def test_missing_optional_field_uses_default() -> None:
    # A trace written by an older/newer version must still load.
    restored = event_from_dict({"type": "AnswerEvent", "text": "hi"})
    assert restored == AnswerEvent(text="hi")


def test_writer_roundtrip_through_file(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    writer = TraceWriter(path)
    for event in ALL_EVENTS:
        writer.write(event)
    writer.close()
    assert read_trace(path) == ALL_EVENTS
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == len(ALL_EVENTS)


def test_writer_creates_file_lazily(tmp_path: Path) -> None:
    path = tmp_path / "unused.jsonl"
    writer = TraceWriter(path)
    writer.close()
    assert not path.exists()  # no empty files for questions that never ran


def test_new_trace_path_is_sortable_and_slugged(tmp_path: Path) -> None:
    path = new_trace_path(tmp_path, "上个月的新增用户数 is what?")
    assert path.parent == tmp_path
    assert path.suffix == ".jsonl"
    assert "/" not in path.name and " " not in path.name


def test_prune_keeps_newest(tmp_path: Path) -> None:
    for i in range(8):
        (tmp_path / f"2026-08-19T00-00-{i:02d}-q.jsonl").write_text("{}\n", encoding="utf-8")
    prune_traces(tmp_path, keep=3)
    remaining = sorted(p.name for p in tmp_path.glob("*.jsonl"))
    assert len(remaining) == 3
    assert remaining[-1].startswith("2026-08-19T00-00-07")


def test_prune_ignores_other_files(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("keep me", encoding="utf-8")
    (tmp_path / "a.jsonl").write_text("{}\n", encoding="utf-8")
    prune_traces(tmp_path, keep=0)
    assert (tmp_path / "notes.txt").exists()
    assert not (tmp_path / "a.jsonl").exists()


def test_retention_counts_the_file_about_to_be_written(tmp_path: Path) -> None:
    # Pruning before creating the next trace leaves keep+1 files on disk.
    for i in range(5):
        (tmp_path / f"2026-08-19T00-00-{i:02d}-q.jsonl").write_text("{}\n", encoding="utf-8")
    prune_traces(tmp_path, keep=3, reserve=1)
    assert len(list(tmp_path.glob("*.jsonl"))) == 2  # room for the incoming one


def test_two_traces_in_the_same_second_do_not_collide(tmp_path: Path) -> None:
    first = new_trace_path(tmp_path, "同一个问题")
    TraceWriter(first).write(AnswerEvent(text="a"))
    second = new_trace_path(tmp_path, "同一个问题")
    assert second != first


def test_crash_truncated_tail_does_not_lose_the_whole_trace(tmp_path: Path) -> None:
    # A process killed mid-write leaves a partial last line — which is exactly
    # the run you most want to replay.
    path = tmp_path / "t.jsonl"
    writer = TraceWriter(path)
    writer.write(ThinkEvent(text="第一步"))
    writer.write(ThinkEvent(text="第二步"))
    writer.close()
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"type": "AnswerEvent", "text": "被截断')

    events = read_trace(path)
    assert events == [ThinkEvent(text="第一步"), ThinkEvent(text="第二步")]


def test_unknown_event_type_skips_only_that_line(tmp_path: Path) -> None:
    # A trace written by a newer version must stay readable by an older one.
    path = tmp_path / "t.jsonl"
    path.write_text(
        '{"type": "ThinkEvent", "text": "before"}\n'
        '{"type": "FutureEvent", "x": 1}\n'
        '{"type": "AnswerEvent", "text": "after"}\n',
        encoding="utf-8",
    )
    events = read_trace(path)
    assert events == [ThinkEvent(text="before"), AnswerEvent(text="after")]
