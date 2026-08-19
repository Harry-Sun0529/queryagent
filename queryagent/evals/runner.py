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
from queryagent.evals.cost import TokenTotals, estimate_cost_usd
from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    ToolCallEvent,
    UsageEvent,
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
    usage: TokenTotals
    model: str


def summarize_events(events: Iterable[AgentEvent]) -> EventSummary:
    """Fold an event stream into the facts the scorers use."""
    pending: dict[str, str] = {}
    executed: list[tuple[str, bool]] = []
    answer_text = ""
    clarify: ClarifyEvent | None = None
    error: ErrorEvent | None = None
    tool_calls = 0
    usage = TokenTotals()
    model = ""
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
        elif isinstance(event, UsageEvent):
            usage = usage + TokenTotals(
                input_tokens=event.input_tokens,
                cached_input_tokens=event.cached_input_tokens,
                output_tokens=event.output_tokens,
                latency_ms=event.latency_ms,
                calls=1,
            )
            model = event.model or model
    final_sql = next((sql for sql, was_error in reversed(executed) if not was_error), None)
    return EventSummary(
        executed_sql=tuple(executed),
        final_sql=final_sql,
        answer_text=answer_text,
        clarify=clarify,
        error=error,
        tool_calls=tool_calls,
        usage=usage,
        model=model,
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
    usage: TokenTotals = TokenTotals()
    model: str = ""
    agent_sql: str = ""  # the SQL that was scored — failure analysis needs it


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
            usage=summary.usage,
            model=summary.model,
        )

    clarify_correct = summary.clarify is None if case.kind == "no_clarify" else None
    metrics_mentioned = None
    if case.kind == "metric" and case.expected_metrics:
        metrics_mentioned = all(name in summary.answer_text for name in case.expected_metrics)

    successful = [sql for sql, was_error in summary.executed_sql if not was_error]
    if not successful:
        detail = summary.error.message if summary.error else "no successful execute_sql call"
        return _failed(
            case,
            detail,
            retries=retries,
            tool_calls=summary.tool_calls,
            clarify_correct=clarify_correct,
            metrics_mentioned=metrics_mentioned,
            usage=summary.usage,
            model=summary.model,
        )
    try:
        expected = connector.execute(case.expected_sql, timeout_s=timeout_s, max_rows=max_rows)
    except QueryError as exc:
        # Unscoreable, but the tokens were still spent — keep them, or the
        # suite's cost and latency totals silently under-count.
        return _failed(
            case,
            f"reference expected_sql failed (case bug?): {exc.original_error}",
            retries=retries,
            tool_calls=summary.tool_calls,
            clarify_correct=clarify_correct,
            metrics_mentioned=metrics_mentioned,
            usage=summary.usage,
            model=summary.model,
        )

    # The case passes when ANY successful SQL reproduces the expected result:
    # agents often run verification queries after the answer-bearing one, so
    # requiring the *last* SQL to be the answer punished good behaviour.
    # Checked last-first (the most likely answer query).
    passed = False
    matched: set[str] = set()
    for sql in dict.fromkeys(reversed(successful)):
        try:
            actual = connector.execute(sql, timeout_s=timeout_s, max_rows=max_rows)
        except QueryError:
            continue
        if rows_match(expected.rows, actual.rows):
            matched.add(sql)
            passed = True
            break
    first_sql, first_was_error = summary.executed_sql[0]
    first_attempt_passed = (
        retries == 0 and not first_was_error and (first_sql in matched or _matches(
            connector, first_sql, expected.rows, timeout_s=timeout_s, max_rows=max_rows
        ))
    )
    return CaseResult(
        case=case,
        passed=passed,
        first_attempt_passed=first_attempt_passed,
        retries=retries,
        tool_calls=summary.tool_calls,
        clarify_correct=clarify_correct,
        metrics_mentioned=metrics_mentioned,
        failure_reason="" if passed else "result sets differ",
        usage=summary.usage,
        model=summary.model,
        agent_sql=next(iter(matched), successful[-1]),
    )


def _matches(
    connector: Connector,
    sql: str,
    expected_rows: tuple[tuple[object, ...], ...],
    *,
    timeout_s: int,
    max_rows: int,
) -> bool:
    try:
        actual = connector.execute(sql, timeout_s=timeout_s, max_rows=max_rows)
    except QueryError:
        return False
    return rows_match(expected_rows, actual.rows)


def _failed(
    case: EvalCase,
    reason: str,
    *,
    retries: int = 0,
    tool_calls: int = 0,
    clarify_correct: bool | None = None,
    metrics_mentioned: bool | None = None,
    usage: TokenTotals | None = None,
    model: str = "",
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
        usage=usage or TokenTotals(),
        model=model,
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
    usage: TokenTotals = TokenTotals()
    model: str = ""
    agent_sql: str = ""  # the SQL that was scored — failure analysis needs it


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
        usage=sum((r.usage for r in results), TokenTotals()),
        model=next((r.model for r in results if r.model), ""),
    )


def render_report(results: Sequence[CaseResult], *, title: str, model_label: str) -> str:
    """Render the markdown report (summary metrics + per-case table)."""
    stats = aggregate(results)
    cost = estimate_cost_usd(stats.usage, stats.model or model_label)
    cases = max(stats.total, 1)
    total_tokens = stats.usage.input_tokens + stats.usage.output_tokens
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
        f"| tokens per case (in+out) | {total_tokens / cases:,.0f} |",
        f"| prompt cache hit rate | {stats.usage.cache_hit_rate:.0%} |",
        f"| latency per case | {stats.usage.latency_ms / cases / 1000:.1f}s |",
        f"| cost per case (upper bound) | "
        f"{'$%.4f' % (cost / cases) if cost is not None else 'n/a'} |",
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
    failures = [r for r in results if not r.passed and r.agent_sql]
    if failures:
        lines += ["", "## Failing cases — SQL comparison", ""]
        for result in failures:
            lines += [
                f"### {result.case.id}",
                "",
                f"- question: {result.case.question.splitlines()[0]}",
                f"- expected: `{' '.join(result.case.expected_sql.split())}`",
                f"- agent: `{' '.join(result.agent_sql.split())}`",
                "",
            ]
    lines.append("")
    return "\n".join(lines)


def _rate(hits: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{hits}/{total} ({hits / total:.0%})"


def _mark(flag: bool) -> str:
    return "✅" if flag else "❌"
