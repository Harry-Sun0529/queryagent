"""``chat``, ``ask`` and ``replay``: consumers of the agent's event stream.

Nothing here decides anything; the loop in ``queryagent.agent`` does. This
wires a backend, a context and tools for one data source, renders events,
and writes the trace.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Protocol

from queryagent.agent import run_agent
from queryagent.budget import (
    BudgetedConnector,
)
from queryagent.cli.errors import _report_error
from queryagent.cli.parser import _local_subject
from queryagent.config import AppConfig, load_config
from queryagent.connectors import make_connector
from queryagent.connectors.base import Connector
from queryagent.context import ContextBuilder
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
from queryagent.llm import make_backend
from queryagent.llm.base import Message
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.schema import render_schema
from queryagent.tools import ToolRegistry, make_clarify_tool, make_default_tools
from queryagent.trace import (
    TRACE_DIR_NAME,
    TraceWriter,
    count_trace_lines,
    new_trace_path,
    prune_traces,
    read_trace,
)
from queryagent.workflow.flowtrace import is_flow_trace, read_flow_trace, render_flow
from queryagent.workflow.wiring import (
    make_budget,
    scan_limit,
)

_trace_notice_shown = False

# Chat turns kept in memory. The prompt side is already trimmed by the
# context budget; this bounds the session's own list, which otherwise grew
# for as long as the session lived.
MAX_REMEMBERED_TURNS = 20

def _make_trace_writer(config: AppConfig, disabled: bool, question: str) -> TraceWriter | None:
    """Build a trace writer unless tracing is off; prunes old traces first."""
    if disabled or not config.trace:
        return None
    directory = Path(config.trace_dir) if config.trace_dir else Path(TRACE_DIR_NAME)
    if directory.exists():
        prune_traces(directory, reserve=1)
    return TraceWriter(new_trace_path(directory, question))


def _finish_trace(writer: TraceWriter | None) -> None:
    """Close the trace and announce it once per process (privacy notice)."""
    global _trace_notice_shown
    if writer is None:
        return
    started = writer.started
    writer.close()
    if started and not _trace_notice_shown:
        _trace_notice_shown = True
        print(
            f"[trace] 已记录到 {writer.path.parent.resolve()}/ —— 含问题、SQL 与查询结果，"
            "可能包含业务数据；该目录已在 .gitignore 中。"
            "关闭方式：--no-trace 或 config 里 trace: false",
            file=sys.stderr,
        )


def _cmd_replay(args: argparse.Namespace) -> int:
    """Re-render a recorded trace (always full detail — that is the point)."""
    if is_flow_trace(args.path):
        # A draft's way to its number (ADR-016), not an agent's event stream.
        steps = read_flow_trace(args.path)
        for line in render_flow(steps):
            print(line)
        _warn_skipped(count_trace_lines(args.path) - len(steps))
        return 0
    events = read_trace(args.path)
    for event in events:
        _render_event(event, verbose=True)
    _warn_skipped(count_trace_lines(args.path) - len(events))
    return 0


def _warn_skipped(skipped: int) -> None:
    """Never hide corruption: a partial tail usually means the run was killed,
    which is itself part of what the replay should tell you."""
    if skipped > 0:
        print(
            f"[warn] {skipped} 行无法解析（通常是进程中断留下的残缺尾行），已跳过",
            file=sys.stderr,
        )

class SessionRunQuestion(Protocol):
    """One-question runner that optionally carries session conversation.

    Structurally a superset of the eval runner's single-arg ``RunQuestion``,
    so the same wired closure serves chat, ask and eval.
    """

    def __call__(
        self, question: str, conversation: Sequence[Message] = ()
    ) -> Iterator[AgentEvent]: ...


def _make_run_question(
    connector: Connector,
    config: AppConfig,
    max_turns: int,
    stack: contextlib.ExitStack,
    *,
    subject: str | None = None,
) -> SessionRunQuestion:
    """Wire backend + context + metrics + tools for one data source.

    The backend owns an HTTP client, so its release is registered on the
    caller's stack: a public eval builds one per database, and leaking a
    connection pool per data source is how a long run runs out of sockets.

    With ``subject``, every statement the model runs is admitted by the
    configured budget under that identity (slice 1E). Eval passes none: it
    is a maintainer measuring, not someone using the data (E02).
    """
    backend = make_backend(config.llm)
    closer = getattr(backend, "close", None)
    if callable(closer):
        stack.callback(closer)
    metric_store = YamlMetricStore(config.metrics_path) if config.metrics_path else None
    builder = ContextBuilder(
        schema_text=render_schema(connector.get_schema()),
        dialect=connector.dialect,
        metric_store=metric_store,
    )
    budgeted = (
        BudgetedConnector(connector, make_budget(config, stack), subject)
        if subject is not None
        else None
    )
    tools = make_default_tools(
        budgeted if budgeted is not None else connector,
        timeout_s=config.safety.timeout_s,
        max_rows=config.safety.max_rows,
    )
    if metric_store is not None:
        # The clarify tool only exists when metrics can actually conflict.
        tools.append(make_clarify_tool())
    registry = ToolRegistry(tools)

    def run_question(
        question: str, conversation: Sequence[Message] = ()
    ) -> Iterator[AgentEvent]:
        if budgeted is not None:
            budgeted.start_request()  # max_queries_per_request counts per question
        return run_agent(
            question,
            backend=backend,
            registry=registry,
            context_builder=builder,
            max_turns=max_turns,
            conversation=conversation,
        )

    return run_question


def _cmd_chat(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    conversation: list[Message] = []
    with contextlib.ExitStack() as stack:
        connector = make_connector(config.database, max_rows_scanned=scan_limit(config))
        stack.callback(connector.close)
        run_question = _make_run_question(
            connector, config, args.max_turns, stack, subject=_local_subject()
        )
        print(
            f"QueryAgent · {config.database.type} · {config.llm.model} "
            "(输入 exit 或 Ctrl-D 退出)"
        )
        while True:
            try:
                question = input("\n你问> ").strip()
            except EOFError:
                break
            if question in {"exit", "quit"}:
                break
            if not question:
                continue
            writer = _make_trace_writer(config, args.no_trace, question)
            try:
                turn = _chat_one_question(
                    question,
                    run_question,
                    conversation=tuple(conversation),
                    verbose=args.verbose,
                    writer=writer,
                )
            except Exception as exc:  # noqa: BLE001
                # One bad turn (a network blip, a rate limit) must not end the
                # session and throw away the conversation built up so far.
                _report_error(exc, verbose=args.verbose)
                turn = None
            finally:
                _finish_trace(writer)
            if turn is not None:
                asked, answered = turn
                # The asked text may carry a clarify reply — follow-ups need
                # that disambiguation, so it is what goes into the memory.
                conversation.append(Message(role="user", content=asked))
                conversation.append(Message(role="assistant", content=answered))
                del conversation[: max(len(conversation) - 2 * MAX_REMEMBERED_TURNS, 0)]
    return 0


def _chat_one_question(
    question: str,
    run_question: SessionRunQuestion,
    *,
    conversation: Sequence[Message] = (),
    verbose: bool,
    writer: TraceWriter | None = None,
) -> tuple[str, str] | None:
    """Run one chat turn (including clarify rounds).

    Returns:
        ``(asked_question, answer_text)`` when the turn produced an answer —
        the caller folds it into the session conversation — else ``None``.
    """
    pending = question
    while True:
        clarify: ClarifyEvent | None = None
        answer_text = ""
        for event in run_question(pending, conversation):
            if writer is not None:
                writer.write(event)
            if isinstance(event, ClarifyEvent):
                clarify = event
            elif isinstance(event, AnswerEvent):
                answer_text = event.text
            _render_event(event, verbose)
        if clarify is None:
            return (pending, answer_text) if answer_text else None
        try:
            reply = input("你答> ").strip()
        except EOFError:
            return None
        if not reply:
            return None
        pending = f"{pending}\n(用户补充说明: {reply})"


def _cmd_ask(args: argparse.Namespace) -> int:
    """One-shot mode: answer/clarify question to stdout, exit code says how.

    0 = answered (or asked a clarifying question — in one-shot mode the
    clarifying question *is* the output); 2 = terminal error event.
    """
    config = load_config(args.config)
    writer = _make_trace_writer(config, args.no_trace, args.question)
    exit_code = 0
    with contextlib.ExitStack() as stack:
        stack.callback(_finish_trace, writer)
        connector = make_connector(config.database, max_rows_scanned=scan_limit(config))
        stack.callback(connector.close)
        run_question = _make_run_question(
            connector, config, args.max_turns, stack, subject=_local_subject()
        )
        for event in run_question(args.question):
            if writer is not None:
                writer.write(event)
            _render_event(event, args.verbose)
            if isinstance(event, ErrorEvent):
                exit_code = 2
    return exit_code

def _render_event(event: AgentEvent, verbose: bool) -> None:
    if isinstance(event, AnswerEvent):
        print(f"\n{event.text}")
    elif isinstance(event, ClarifyEvent):
        print(f"\n[?] {event.question}")
    elif isinstance(event, ErrorEvent):
        print(f"[ERROR] {event.error_type}: {event.message}", file=sys.stderr)
    elif not verbose:
        return
    elif isinstance(event, ThinkEvent):
        print(f"[THINK] {event.text}")
    elif isinstance(event, ToolCallEvent):
        print(f"[ACT] {event.tool_name} {event.arguments}")
    elif isinstance(event, ObservationEvent):
        prefix = "[OBSERVE:ERROR]" if event.is_error else "[OBSERVE]"
        print(f"{prefix}\n{event.content}")
    elif isinstance(event, RetryEvent):
        print(f"[RETRY #{event.attempt}] {event.reason}")
    elif isinstance(event, UsageEvent):
        cached = f", cached {event.cached_input_tokens}" if event.cached_input_tokens else ""
        print(
            f"[USAGE] {event.model} in={event.input_tokens}{cached} "
            f"out={event.output_tokens} {event.latency_ms}ms"
        )
