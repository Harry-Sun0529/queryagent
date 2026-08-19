"""Unit tests for the eval runner, driven by scripted event streams.

No agent implementation needed: the runner consumes the event-stream seam,
so these tests script events exactly the way run_agent will produce them.
"""

from __future__ import annotations

from collections.abc import Iterator

from queryagent.connectors.base import QueryResult
from queryagent.errors import QueryError, SafetyViolation
from queryagent.evals.cases import EvalCase
from queryagent.evals.runner import aggregate, render_report, run_case, summarize_events
from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    ToolCallEvent,
)


class FakeConnector:
    """Returns canned results per SQL string; raises QueryError otherwise."""

    dialect = "sqlite"

    def __init__(self, results: dict[str, tuple[tuple[object, ...], ...]]) -> None:
        self._results = results

    def execute(self, sql: str, *, timeout_s: int, max_rows: int) -> QueryResult:
        if sql not in self._results:
            raise QueryError(f"no such result for: {sql}", dialect=self.dialect)
        rows = self._results[sql]
        return QueryResult(columns=("c",), rows=rows, elapsed_ms=1, truncated=False)

    def get_schema(self) -> list[object]:
        return []

    def close(self) -> None:
        pass


def sql_events(sql: str, *, error: bool = False, call_id: str = "c1") -> list[AgentEvent]:
    return [
        ToolCallEvent(tool_name="execute_sql", arguments={"sql": sql}, tool_call_id=call_id),
        ObservationEvent(content="...", is_error=error, tool_call_id=call_id),
    ]


def scripted(events: list[AgentEvent]) -> Iterator[AgentEvent]:
    yield from events


def simple_case(**overrides: object) -> EvalCase:
    fields: dict[str, object] = {
        "id": "t1",
        "question": "q",
        "kind": "simple",
        "expected_sql": "SELECT ref",
    }
    fields.update(overrides)
    return EvalCase(**fields)  # type: ignore[arg-type]


def test_pass_on_first_attempt() -> None:
    events = sql_events("SELECT agent") + [AnswerEvent(text="42")]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    assert result.passed and result.first_attempt_passed
    assert result.retries == 0
    assert result.tool_calls == 1


def test_self_repair_counts_retry() -> None:
    events = (
        sql_events("SELECT broken", error=True, call_id="c1")
        + sql_events("SELECT agent", call_id="c2")
        + [AnswerEvent(text="42")]
    )
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    assert result.passed
    assert not result.first_attempt_passed
    assert result.retries == 1


def test_verification_query_after_answer_still_passes() -> None:
    # Agents often run a sanity-check query AFTER the answer-bearing one;
    # any successful SQL reproducing the expected result counts.
    events = (
        sql_events("SELECT agent", call_id="c1")
        + sql_events("SELECT check", call_id="c2")
        + [AnswerEvent(text="42")]
    )
    connector = FakeConnector(
        {
            "SELECT ref": ((42,),),
            "SELECT agent": ((42,),),
            "SELECT check": ((42, 42),),  # different shape, does not match
        }
    )
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    assert result.passed
    assert result.first_attempt_passed  # first SQL matched, zero retries


def test_wrong_result_fails() -> None:
    events = sql_events("SELECT agent") + [AnswerEvent(text="7")]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((7,),)})
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    assert not result.passed
    assert result.failure_reason == "result sets differ"


def test_no_successful_sql_fails() -> None:
    events: list[AgentEvent] = [ErrorEvent(error_type="MaxTurns", message="turn limit")]
    result = run_case(
        simple_case(),
        run_question=lambda q: scripted(events),
        connector=FakeConnector({"SELECT ref": ((42,),)}),
    )
    assert not result.passed
    assert "turn limit" in result.failure_reason


def test_agent_crash_is_case_failure_not_suite_crash() -> None:
    def crashing(question: str) -> Iterator[AgentEvent]:
        raise SafetyViolation("blocked", sql="DROP TABLE users")
        yield  # pragma: no cover

    result = run_case(
        simple_case(), run_question=crashing, connector=FakeConnector({})
    )
    assert not result.passed
    assert "SafetyViolation" in result.failure_reason


def test_clarify_case_passes_when_metrics_named() -> None:
    events: list[AgentEvent] = [
        ClarifyEvent(question="哪种口径？", conflicting_metrics=("new_users",))
    ]
    case = simple_case(kind="clarify", expected_sql="", expected_metrics=("new_users",))
    result = run_case(
        case, run_question=lambda q: scripted(events), connector=FakeConnector({})
    )
    assert result.passed and result.clarify_correct


def test_clarify_case_fails_without_clarify_event() -> None:
    events = sql_events("SELECT agent") + [AnswerEvent(text="guessed")]
    case = simple_case(kind="clarify", expected_sql="", expected_metrics=("new_users",))
    result = run_case(
        case, run_question=lambda q: scripted(events), connector=FakeConnector({})
    )
    assert not result.passed and result.clarify_correct is False


def test_no_clarify_control_flags_unwanted_clarify() -> None:
    events: list[AgentEvent] = [
        ClarifyEvent(question="哪种口径？", conflicting_metrics=("new_users",)),
        *sql_events("SELECT agent"),
        AnswerEvent(text="42"),
    ]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    case = simple_case(kind="no_clarify")
    result = run_case(case, run_question=lambda q: scripted(events), connector=connector)
    assert result.passed  # result still correct
    assert result.clarify_correct is False  # but clarify behaviour was wrong


def test_metric_mention_checked_in_answer() -> None:
    events = sql_events("SELECT agent") + [AnswerEvent(text="按「新增用户」口径：42")]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    case = simple_case(kind="metric", expected_metrics=("新增用户",))
    result = run_case(case, run_question=lambda q: scripted(events), connector=connector)
    assert result.passed and result.metrics_mentioned is True


def test_aggregate_and_report() -> None:
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    ok = run_case(
        simple_case(),
        run_question=lambda q: scripted(sql_events("SELECT agent") + [AnswerEvent(text="42")]),
        connector=connector,
    )
    clarify_ok = run_case(
        simple_case(id="t2", kind="clarify", expected_sql="", expected_metrics=("m",)),
        run_question=lambda q: scripted(
            [ClarifyEvent(question="?", conflicting_metrics=("m",))]
        ),
        connector=connector,
    )
    stats = aggregate([ok, clarify_ok])
    assert stats.total == 2
    assert stats.result_cases == 1 and stats.final_pass == 1
    assert stats.clarify_cases == 1 and stats.clarify_correct == 1
    report = render_report([ok, clarify_ok], title="T", model_label="test-model")
    assert "first-execution pass rate" in report
    assert "clarify-behaviour accuracy" in report
    assert "test-model" in report
    assert "| t1 |" in report and "| t2 |" in report


def test_summarize_pairs_sql_with_observations_by_id() -> None:
    events: list[AgentEvent] = [
        ToolCallEvent(tool_name="get_schema", arguments={}, tool_call_id="s1"),
        ObservationEvent(content="schema", is_error=False, tool_call_id="s1"),
        *sql_events("SELECT 1", call_id="c9"),
        AnswerEvent(text="done"),
    ]
    summary = summarize_events(events)
    assert summary.executed_sql == (("SELECT 1", False),)
    assert summary.final_sql == "SELECT 1"
    assert summary.tool_calls == 2


def usage_events(*specs: tuple[int, int, int, int]) -> list[AgentEvent]:
    from queryagent.events import UsageEvent

    return [
        UsageEvent(
            model="deepseek-v4-flash",
            input_tokens=i,
            output_tokens=o,
            cached_input_tokens=c,
            latency_ms=ms,
        )
        for i, c, o, ms in specs
    ]


def test_case_result_accumulates_usage() -> None:
    events = [
        *usage_events((1000, 800, 50, 900), (1500, 1400, 90, 1100)),
        *sql_events("SELECT agent"),
        AnswerEvent(text="42"),
    ]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    assert result.usage.input_tokens == 2500
    assert result.usage.cached_input_tokens == 2200
    assert result.usage.output_tokens == 140
    assert result.usage.latency_ms == 2000
    assert result.usage.calls == 2
    assert result.model == "deepseek-v4-flash"


def test_report_includes_cost_latency_and_cache_metrics() -> None:
    events = [
        *usage_events((1000, 800, 50, 900)),
        *sql_events("SELECT agent"),
        AnswerEvent(text="42"),
    ]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    report = render_report([result], title="T", model_label="deepseek-v4-flash")
    assert "cache hit rate" in report
    assert "80%" in report  # 800/1000 cached
    assert "tokens per case" in report
    assert "latency per case" in report
    assert "cost" in report.lower()


def test_report_handles_unpriced_model_without_crashing() -> None:
    events = [
        *usage_events((1000, 0, 50, 900)),
        *sql_events("SELECT agent"),
        AnswerEvent(text="42"),
    ]
    connector = FakeConnector({"SELECT ref": ((42,),), "SELECT agent": ((42,),)})
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    report = render_report([result], title="T", model_label="mystery-model-9000")
    assert "n/a" in report  # cost unknown, never fabricated


def test_usage_is_kept_when_the_reference_sql_is_broken() -> None:
    # Tokens were spent even though the case is unscoreable; dropping them
    # makes the suite's cost and latency totals silently under-count.
    events = [
        *usage_events((900, 700, 40, 800)),
        *sql_events("SELECT agent"),
        AnswerEvent(text="42"),
    ]
    connector = FakeConnector({"SELECT agent": ((42,),)})  # no "SELECT ref"
    result = run_case(
        simple_case(), run_question=lambda q: scripted(events), connector=connector
    )
    assert not result.passed
    assert "reference expected_sql failed" in result.failure_reason
    assert result.usage.input_tokens == 900
    assert result.usage.calls == 1
    assert result.model == "deepseek-v4-flash"
