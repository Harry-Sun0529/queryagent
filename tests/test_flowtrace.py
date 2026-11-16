"""Plan 3 / ADR-016: the confirmed flow leaves a trace of how a number came about.

Refusals are asserted as pairs: the refusal is traced, and nothing that
comes after it is.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from queryagent.cli import main
from queryagent.workflow import flowtrace
from queryagent.workflow.errors import ConfirmationRequired, PermissionDenied, StaleVersion
from queryagent.workflow.flowtrace import (
    ADMITTED,
    AMENDED,
    CONFIRMED,
    EXECUTED,
    PREPARED,
    REFUSED,
    FlowEvent,
    FlowTraceWriter,
    is_flow_trace,
    read_flow_trace,
    render_flow,
)
from queryagent.workflow.models import ActorContext, Channel, Rule, RuleSource
from queryagent.workflow.service import QueryWorkflow
from tests.wired import AGENT, ALICE, ALICE_WEB, Parts


class Traced:
    """A wired workflow whose every flow event is kept."""

    def __init__(self, tmp_path: Path) -> None:
        self.parts = Parts(tmp_path)
        self.events: list[FlowEvent] = []
        inner = self.parts.workflow
        self.workflow = QueryWorkflow(
            store=self.parts.store,
            builder=inner._builder,  # noqa: SLF001
            compiler=inner._compiler,  # noqa: SLF001
            executor=inner._execute_sql,  # noqa: SLF001
            emit=self.events.append,
        )

    def kinds(self, draft_id: str | None = None) -> list[str]:
        return [e.kind for e in self.events if draft_id is None or e.draft_id == draft_id]

    def confirmed_draft(self, actor: ActorContext = ALICE) -> str:
        draft = self.workflow.prepare(actor, "新增用户有多少？", request_id="r")
        draft = self.workflow.amend(
            actor,
            draft.draft_id,
            expected_version=draft.version,
            rules=(Rule("variant", "registered", RuleSource.USER),),
        )
        self.workflow.confirm(
            actor, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )
        return draft.draft_id


@pytest.fixture(autouse=True)
def _each_test_is_its_own_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first-write notice is said once per process; give every test a fresh one."""
    monkeypatch.setattr(flowtrace, "_announced", False)


@pytest.fixture
def traced(tmp_path: Path):  # type: ignore[no-untyped-def]
    built = Traced(tmp_path)
    yield built
    built.parts.close()


def test_a_flow_from_question_to_number_is_traced_in_order(traced: Traced) -> None:
    """V1."""
    draft_id = traced.confirmed_draft()
    run = traced.workflow.execute_confirmed(ALICE, draft_id)
    assert traced.kinds(draft_id) == [PREPARED, AMENDED, CONFIRMED, ADMITTED, EXECUTED]
    executed = traced.events[-1]
    assert executed.detail["status"] == "succeeded"
    assert executed.detail["sql"] == run.sql
    assert executed.detail["row_count"] == 1
    assert "rows" not in executed.detail  # the numbers themselves stay in the state file
    assert {(e.subject, e.workspace, e.channel) for e in traced.events} == {
        ("alice", "ops", "cli")
    }


def test_running_a_spent_confirmation_again_is_traced_as_a_replay_and_runs_nothing(
    traced: Traced,
) -> None:
    draft_id = traced.confirmed_draft()
    traced.workflow.execute_confirmed(ALICE, draft_id)
    before = len(traced.parts.executed)
    traced.workflow.execute_confirmed(ALICE, draft_id)
    assert traced.kinds(draft_id)[-1] == ADMITTED
    assert "没有执行新的语句" in traced.events[-1].detail["answered_with"]
    assert len(traced.parts.executed) == before


def test_executing_without_a_confirmation_is_traced_as_refused_and_nothing_after(
    traced: Traced,
) -> None:
    """V2, as a pair: the refusal is there, and no admission or execution is."""
    draft = traced.workflow.prepare(AGENT, "新增用户有多少？", request_id="r")
    with pytest.raises(ConfirmationRequired, match="还没有人确认"):
        traced.workflow.execute_confirmed(AGENT, draft.draft_id)
    kinds = traced.kinds(draft.draft_id)
    assert kinds == [PREPARED, REFUSED]
    refusal = traced.events[-1].detail
    assert (refusal["step"], refusal["refusal"]) == ("execute", "ConfirmationRequired")
    assert traced.parts.executed == []


def test_each_refusal_is_traced_once_with_its_step(traced: Traced) -> None:
    draft = traced.workflow.prepare(ALICE, "新增用户有多少？", request_id="r")
    with pytest.raises(PermissionDenied, match="Agent 通道不能确认"):
        traced.workflow.confirm(
            AGENT, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )
    with pytest.raises(StaleVersion, match="is at version 1"):
        traced.workflow.confirm(ALICE, draft.draft_id, version=9, definition_hash="x")
    with pytest.raises(StaleVersion, match="not 7"):
        traced.workflow.amend(
            ALICE,
            draft.draft_id,
            expected_version=7,
            rules=(Rule("variant", "registered", RuleSource.USER),),
        )
    refused = [(e.channel, e.detail["step"], e.detail["refusal"]) for e in traced.events[1:]]
    assert refused == [
        ("mcp", "confirm", "PermissionDenied"),
        ("cli", "confirm", "StaleVersion"),
        ("cli", "amend", "StaleVersion"),
    ]
    assert CONFIRMED not in traced.kinds() and AMENDED not in traced.kinds()


def test_a_refused_reach_into_another_workspace_is_filed_under_the_callers_own(
    traced: Traced, tmp_path: Path
) -> None:
    """The finance draft's trace gains nothing; ops's refusal says nothing of what is there."""
    finance = ActorContext(subject_id="alice", workspace_id="finance", channel=Channel.WEB)
    draft_id = traced.confirmed_draft(finance)
    with pytest.raises(PermissionDenied, match="not permitted"):
        traced.workflow.execute_confirmed(ALICE, draft_id)
    refusal = traced.events[-1]
    assert (refusal.kind, refusal.workspace) == (REFUSED, "ops")
    assert refusal.detail["message"] == "not permitted"
    writer = FlowTraceWriter(tmp_path / "traces", warn=lambda _text: None)
    for event in traced.events:
        writer.write(event)
    finance_file = writer.path_of(draft_id, "finance").read_text(encoding="utf-8")
    ops_file = writer.path_of(draft_id, "ops").read_text(encoding="utf-8")
    assert "refused" not in finance_file
    assert ops_file.count("\n") == 1 and "registered" not in ops_file
    assert traced.parts.executed == []


def test_the_three_doors_leave_the_same_trace(tmp_path: Path) -> None:
    """V4: events come from the service, so a door cannot tell it differently."""
    shapes = []
    for index, (prepares, confirms, runs) in enumerate(
        [(ALICE, ALICE, ALICE), (AGENT, ALICE_WEB, AGENT), (AGENT, ALICE, AGENT)]
    ):
        (tmp_path / str(index)).mkdir()
        traced = Traced(tmp_path / str(index))
        draft = traced.workflow.prepare(prepares, "新增用户有多少？", request_id="r")
        draft = traced.workflow.amend(
            prepares,
            draft.draft_id,
            expected_version=1,
            rules=(Rule("variant", "registered", prepares.authoring_source),),
        )
        traced.workflow.confirm(
            confirms, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )
        traced.workflow.execute_confirmed(runs, draft.draft_id)
        shapes.append(traced.kinds())
        assert [e.channel for e in traced.events][2] == confirms.channel.value
        traced.parts.close()
    assert shapes[0] == shapes[1] == shapes[2]


def test_what_a_builder_notes_is_traced_under_the_draft_being_prepared(traced: Traced) -> None:
    class Noting:
        def build(self, question: str, actor: ActorContext | None = None):  # type: ignore[no-untyped-def]
            dropped = [{"key": "dedup", "reason": "引文对不上"}]
            flowtrace.note("extracted", adopted=[], dropped=dropped)
            return traced.parts.workflow._builder.build(question)  # noqa: SLF001

    traced.workflow._builder = Noting()  # type: ignore[assignment]  # noqa: SLF001
    draft = traced.workflow.prepare(ALICE, "新增用户有多少？", request_id="r")
    assert traced.kinds(draft.draft_id) == ["extracted", PREPARED]
    assert traced.events[0].detail["dropped"][0]["reason"] == "引文对不上"


def test_a_note_outside_any_draft_goes_nowhere() -> None:
    flowtrace.note("extracted", adopted=[], dropped=[])  # must not raise


def test_without_an_emitter_nothing_is_traced_and_nothing_breaks(tmp_path: Path) -> None:
    parts = Parts(tmp_path)
    draft = parts.workflow.prepare(ALICE, "新增用户有多少？", request_id="r")
    assert draft.version == 1
    parts.close()


# ------------------------------------------------------------------ the file


def _event(draft: str = "d1", workspace: str = "ops", **detail: object) -> FlowEvent:
    at = "2026-11-16T10:00:00+00:00"
    return FlowEvent(PREPARED, draft, at, "alice", workspace, "cli", detail)


def test_each_draft_and_workspace_has_its_own_file_and_lines_append(tmp_path: Path) -> None:
    said: list[str] = []
    writer = FlowTraceWriter(tmp_path, warn=said.append)
    writer.write(_event(question="一"))
    FlowTraceWriter(tmp_path, warn=said.append).write(_event(question="二"))  # another writer
    writer.write(_event(draft="d2"))
    first = read_flow_trace(writer.path_of("d1", "ops"))
    assert [e.detail["question"] for e in first] == ["一", "二"]
    assert len(read_flow_trace(writer.path_of("d2", "ops"))) == 1
    assert sum("已记录到" in text for text in said) == 1  # once per process, not per writer


def test_a_trace_that_cannot_be_written_warns_once_and_never_raises(tmp_path: Path) -> None:
    """V8: observation only. A full disk must not be why a number was not produced."""
    blocker = tmp_path / "traces"
    blocker.write_text("a file where the directory should be", encoding="utf-8")
    said: list[str] = []
    writer = FlowTraceWriter(blocker, warn=said.append)
    writer.write(_event())
    writer.write(_event())
    assert len(said) == 1 and "流程照常继续" in said[0]


def test_a_partial_last_line_costs_that_line_only(tmp_path: Path) -> None:
    writer = FlowTraceWriter(tmp_path, warn=lambda _t: None)
    writer.write(_event(question="完整的一行"))
    path = writer.path_of("d1", "ops")
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"type": "FlowEvent", "kind": "exec')
    assert is_flow_trace(path)
    assert [e.detail["question"] for e in read_flow_trace(path)] == ["完整的一行"]


def test_old_draft_traces_are_pruned(tmp_path: Path) -> None:
    directory = tmp_path / "flows"
    directory.mkdir()
    for index in range(5):
        (directory / f"d{index}-ops.jsonl").write_text("{}\n", encoding="utf-8")
    flowtrace.prune_flow_traces(directory, keep=3, reserve=1)
    assert len(list(directory.glob("*.jsonl"))) == 2


def test_rendering_says_what_was_dropped_and_what_was_refused() -> None:
    events = [
        FlowEvent("extracted", "d" * 32, "2026-11-16T10:00:00+00:00", "alice", "ops", "cli", {
            "adopted": [{"key": "filters", "value": "不含测试账号", "ref": "doc#c1"}],
            "dropped": [{"key": "dedup", "reason": "引文不是被引片段的逐字子串", "citation": 2}],
        }),
        FlowEvent(REFUSED, "d" * 32, "2026-11-16T10:00:05+00:00", "alice", "ops", "mcp", {
            "step": "execute", "refusal": "ConfirmationRequired", "message": "还没有人确认",
        }),
    ]
    text = "\n".join(render_flow(events))
    assert "采纳 filters：不含测试账号" in text
    assert "✗ 丢弃 dedup：引文不是被引片段的逐字子串" in text
    assert "✗ 拒绝" in text and "还没有人确认" in text and "[mcp]" in text


# ---------------------------------------------------- through the real doors


def _flow_config(parts: Parts, trace_dir: Path | None) -> Path:
    path = parts.write_config()
    text = path.read_text(encoding="utf-8")
    if trace_dir is not None:
        text = text.replace("trace: false\n", f"trace: true\ntrace_dir: {trace_dir}\n")
    path.write_text(text, encoding="utf-8")
    return path


def test_the_cli_writes_a_trace_that_replay_can_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """V1 + V9 through the product path."""
    parts = Parts(tmp_path)
    traces = tmp_path / "traces"
    config = _flow_config(parts, traces)
    alice = ["--subject", "alice", "--workspace", "ops"]
    code = main(
        ["flow", "新增用户有多少？", "--config", str(config), *alice,
         "--variant", "registered", "--yes"]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "已记录到" in captured.err  # ADR-005: said on first write
    (written,) = list((traces / "flows").glob("*.jsonl"))
    kinds = [e.kind for e in read_flow_trace(written)]
    assert kinds == [PREPARED, AMENDED, CONFIRMED, ADMITTED, EXECUTED]
    assert main(["replay", str(written)]) == 0
    shown = capsys.readouterr().out
    assert "确认流记录" in shown and "执行" in shown and "SELECT COUNT(*)" in shown
    parts.close()


def test_trace_false_writes_no_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """V6."""
    parts = Parts(tmp_path)
    config = _flow_config(parts, None)
    code = main(
        ["flow", "新增用户有多少？", "--config", str(config), "--subject", "alice",
         "--workspace", "ops", "--variant", "registered", "--yes"]
    )
    assert code == 0
    assert not list(tmp_path.rglob("flows"))
    assert "[trace]" not in capsys.readouterr().err
    parts.close()


def test_an_agent_trace_is_still_replayed_as_before(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """V9: the other kind of trace is told apart by its first line."""
    path = tmp_path / "agent.jsonl"
    path.write_text(json.dumps({"type": "AnswerEvent", "text": "共 3 人"}) + "\n", encoding="utf-8")
    assert not is_flow_trace(path)
    assert main(["replay", str(path)]) == 0
    assert "共 3 人" in capsys.readouterr().out


def test_the_state_file_is_untouched_by_tracing(traced: Traced) -> None:
    draft_id = traced.confirmed_draft()
    traced.workflow.execute_confirmed(ALICE, draft_id)
    with sqlite3.connect(traced.parts.state) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert not any("trace" in name or "event" in name for name in tables)
