"""Eval runner: drives the agent's event stream per case and scores it.

The runner never imports ``agent.py`` — it consumes a ``run_question``
callable returning the event stream, so it is fully testable with scripted
events today and works unchanged with the human's agent implementation
(spec §二: the event stream is the seam every consumer shares).

Five report metrics (spec §三 v0.2.0):
first-execution pass rate, pass rate after self-repair, metric hit rate,
average tool calls, clarify-behaviour accuracy.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from queryagent.connectors.base import Connector
from queryagent.errors import QueryError
from queryagent.evals.cases import EvalCase
from queryagent.evals.compare import rows_match
from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    ToolCallEvent,
)

RunQuestion = Callable[[str], Iterable[AgentEvent]]


@dataclass(frozen=True)
class EventSummary:
    """What the runner needs to know about one agent run."""

    executed_sql: tuple[tuple[str, bool], ...]  # (sql, was_error) in order
    final_sql: str | None  # last successfully executed SQL
    answer_text: str
    clarify: ClarifyEvent | None
    error: ErrorEvent | None
    tool_calls: int


def summarize_events(events: Iterable[AgentEvent]) -> EventSummary:
    """Fold an event stream into the facts the scorers use."""
    pending: dict[str, str] = {}
    executed: list[tuple[str, bool]] = []
    answer_text = ""
    clarify: ClarifyEvent | None = None
    error: ErrorEvent | None = None
    tool_calls = 0
    for event in events:
        if isinstance(event, ToolCallEvent):
            tool_calls += 1
            if event.tool_name == "execute_sql":
                pending[event.tool_call_id] = str(event.arguments.get("sql", ""))
        elif isinstance(event, ObservationEvent) and event.tool_call_id in pending:
            executed.append((pending.pop(event.tool_call_id), event.is_error))
        elif isinstance(event, AnswerEvent):
            answer_text = event.text
        elif isinstance(event, ClarifyEvent) and clarify is None:
            clarify = event
        elif isinstance(event, ErrorEvent):
            error = event
    final_sql = next((sql for sql, was_error in reversed(executed) if not was_error), None)
    return EventSummary(
        executed_sql=tuple(executed),
        final_sql=final_sql,
        answer_text=answer_text,
        clarify=clarify,
        error=error,
        tool_calls=tool_calls,
    )


@dataclass(frozen=True)
class CaseResult:
    """Score for one case."""

    case: EvalCase
    passed: bool
    first_attempt_passed: bool
    retries: int
    tool_calls: int
    clarify_correct: bool | None
    metrics_mentioned: bool | None
    failure_reason: str = ""


def run_case(
    case: EvalCase,
    *,
    run_question: RunQuestion,
    connector: Connector,
    timeout_s: int = 30,
    max_rows: int = 1000,
) -> CaseResult:
    """Run one case end to end and score it.

    Agent crashes are converted into failed results (the suite must finish
    even when individual cases blow up).
    """
    try:
        summary = summarize_events(run_question(case.question))
    except Exception as exc:  # noqa: BLE001 - any agent crash is a case failure
        return _failed(case, f"agent raised {type(exc).__name__}: {exc}")
    retries = sum(1 for _, was_error in summary.executed_sql if was_error)

    if case.kind == "clarify":
        ok = summary.clarify is not None and all(
            name in summary.clarify.conflicting_metrics for name in case.expected_metrics
        )
        reason = "" if ok else "expected a ClarifyEvent naming the conflicting metrics"
        return CaseResult(
            case=case,
            passed=ok,
            first_attempt_passed=ok,
            retries=retries,
            tool_calls=summary.tool_calls,
            clarify_correct=ok,
            metrics_mentioned=None,
            failure_reason=reason,
        )

    clarify_correct = summary.clarify is None if case.kind == "no_clarify" else None
    metrics_mentioned = None
    if case.kind == "metric" and case.expected_metrics:
        metrics_mentioned = all(name in summary.answer_text for name in case.expected_metrics)

    if summary.final_sql is None:
        detail = summary.error.message if summary.error else "no successful execute_sql call"
        return _failed(
            case,
            detail,
            retries=retries,
            tool_calls=summary.tool_calls,
            clarify_correct=clarify_correct,
            metrics_mentioned=metrics_mentioned,
        )
    try:
        expected = connector.execute(case.expected_sql, timeout_s=timeout_s, max_rows=max_rows)
    except QueryError as exc:
        return _failed(case, f"reference expected_sql failed (case bug?): {exc.original_error}")
    try:
        actual = connector.execute(summary.final_sql, timeout_s=timeout_s, max_rows=max_rows)
    except QueryError as exc:
        return _failed(
            case,
            f"agent SQL failed on re-execution: {exc.original_error}",
            retries=retries,
            tool_calls=summary.tool_calls,
            clarify_correct=clarify_correct,
            metrics_mentioned=metrics_mentioned,
        )
    passed = rows_match(expected.rows, actual.rows)
    return CaseResult(
        case=case,
        passed=passed,
        first_attempt_passed=passed and retries == 0,
        retries=retries,
        tool_calls=summary.tool_calls,
        clarify_correct=clarify_correct,
        metrics_mentioned=metrics_mentioned,
        failure_reason="" if passed else "result sets differ",
    )


def _failed(
    case: EvalCase,
    reason: str,
    *,
    retries: int = 0,
    tool_calls: int = 0,
    clarify_correct: bool | None = None,
    metrics_mentioned: bool | None = None,
) -> CaseResult:
    return CaseResult(
        case=case,
        passed=False,
        first_attempt_passed=False,
        retries=retries,
        tool_calls=tool_calls,
        clarify_correct=clarify_correct,
        metrics_mentioned=metrics_mentioned,
        failure_reason=reason,
    )


@dataclass(frozen=True)
class EvalStats:
    """Aggregated counters behind the five report metrics."""

    total: int
    result_cases: int
    first_pass: int
    final_pass: int
    metric_cases: int
    metric_hits: int
    clarify_cases: int
    clarify_correct: int
    avg_tool_calls: float


def aggregate(results: Sequence[CaseResult]) -> EvalStats:
    """Compute the aggregate counters from per-case results."""
    result_cases = [r for r in results if r.case.kind != "clarify"]
    metric_results = [r for r in results if r.metrics_mentioned is not None]
    clarify_results = [r for r in results if r.clarify_correct is not None]
    total = len(results)
    return EvalStats(
        total=total,
        result_cases=len(result_cases),
        first_pass=sum(1 for r in result_cases if r.first_attempt_passed),
        final_pass=sum(1 for r in result_cases if r.passed),
        metric_cases=len(metric_results),
        metric_hits=sum(1 for r in metric_results if r.metrics_mentioned),
        clarify_cases=len(clarify_results),
        clarify_correct=sum(1 for r in clarify_results if r.clarify_correct),
        avg_tool_calls=(sum(r.tool_calls for r in results) / total) if total else 0.0,
    )


def render_report(results: Sequence[CaseResult], *, title: str, model_label: str) -> str:
    """Render the markdown report (summary metrics + per-case table)."""
    stats = aggregate(results)
    lines = [
        f"# {title}",
        "",
        f"- model: `{model_label}`",
        f"- cases: {stats.total}",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "|---|---|",
        f"| first-execution pass rate | {_rate(stats.first_pass, stats.result_cases)} |",
        f"| pass rate after self-repair | {_rate(stats.final_pass, stats.result_cases)} |",
        f"| metric hit rate | {_rate(stats.metric_hits, stats.metric_cases)} |",
        f"| clarify-behaviour accuracy | {_rate(stats.clarify_correct, stats.clarify_cases)} |",
        f"| average tool calls | {stats.avg_tool_calls:.2f} |",
        "",
        "## Cases",
        "",
        "| id | kind | passed | first try | retries | tool calls | note |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result.case.id} | {result.case.kind} | {_mark(result.passed)} "
            f"| {_mark(result.first_attempt_passed)} | {result.retries} "
            f"| {result.tool_calls} | {result.failure_reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def _rate(hits: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{hits}/{total} ({hits / total:.0%})"


def _mark(flag: bool) -> str:
    return "✅" if flag else "❌"
