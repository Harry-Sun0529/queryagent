"""A killed writer must not destroy either completed or newly appended cases."""

from pathlib import Path

from queryagent.evals.cases import EvalCase
from queryagent.evals.checkpoint import ResultLog
from queryagent.evals.runner import CaseResult


def scored(case_id: str) -> CaseResult:
    return CaseResult(
        EvalCase(case_id, "中文问题", "simple", "SELECT 1"), True, True, 0, 1, None, None
    )


def test_resume_append_survives_partial_tail(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    log = ResultLog(path, signature="same")
    log.append(scored("before"))
    log.close()
    with path.open("ab") as stream:
        stream.write(b'{"case":')
    resumed = ResultLog(path, resume=True, signature="same")
    resumed.append(scored("after"))
    resumed.close()
    assert set(ResultLog(path, resume=True, signature="same").completed()) == {"before", "after"}


def test_incomplete_utf8_only_loses_its_line(tmp_path: Path) -> None:
    from queryagent.events import AnswerEvent
    from queryagent.trace import TraceWriter, count_trace_lines, read_trace

    path = tmp_path / "results.jsonl"
    log = ResultLog(path, signature="same")
    log.append(scored("before"))
    log.close()
    trace = tmp_path / "trace.jsonl"
    writer = TraceWriter(trace)
    writer.write(AnswerEvent(text="完整答案"))
    writer.close()
    for file in (path, trace):
        with file.open("ab") as stream:
            stream.write(b"\xe4\xb8")
    resumed = ResultLog(path, resume=True, signature="same")
    assert set(resumed.completed()) == {"before"}
    resumed.append(scored("after"))
    resumed.close()
    assert set(ResultLog(path, resume=True).completed()) == {"before", "after"}
    assert read_trace(trace) == [AnswerEvent(text="完整答案")]
    assert count_trace_lines(trace) == 2


def test_run_cannot_resume_log_without_identity(tmp_path: Path) -> None:
    import json

    import pytest

    from queryagent.evals.checkpoint import ResumeMismatch, result_to_dict

    path = tmp_path / "legacy.jsonl"
    path.write_text(json.dumps(result_to_dict(scored("old"))) + "\n")
    assert set(ResultLog(path, resume=True).completed()) == {"old"}
    with pytest.raises(ResumeMismatch):
        ResultLog(path, resume=True, signature="new-experiment")
