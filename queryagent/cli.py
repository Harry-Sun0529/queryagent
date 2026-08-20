"""QueryAgent CLI: ``chat`` (interactive, multi-turn), ``ask`` (one-shot),
``eval`` (scored suites) — all pure consumers of the AgentEvent stream.

``--verbose`` renders the full THINK/ACT/OBSERVE trace; the default shows
answers only. In chat, a ClarifyEvent renders the agent's question, folds
the user's reply back into the pending question and re-runs; answered turns
are kept as session conversation so follow-ups can refer back.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import sys
import traceback
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Protocol

from queryagent.agent import run_agent
from queryagent.config import AppConfig, load_config
from queryagent.connectors import make_connector
from queryagent.connectors.base import Connector
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.context import ContextBuilder
from queryagent.errors import ConnectorError, QueryAgentError, is_transient
from queryagent.evals.cases import EvalCase, load_cases
from queryagent.evals.checkpoint import ResultLog, ResumeMismatch
from queryagent.evals.public import load_subset
from queryagent.evals.runner import (
    CaseResult,
    render_report,
    run_case,
    unscoreable_case,
)
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

_trace_notice_shown = False

# Consecutive cases lost to an unreachable provider before a run gives up.
# Burning a 200-case suite against a dead endpoint produces a report that
# reads like a measurement of 0%; stopping early keeps it honest and, thanks
# to checkpointing, costs nothing to resume.
MAX_CONSECUTIVE_OUTAGES = 5


class UpstreamOutage(Exception):
    """Too many consecutive cases could not reach the provider."""


class _OutageGuard:
    """Counts consecutive unmeasured cases across the whole suite."""

    def __init__(self, limit: int = MAX_CONSECUTIVE_OUTAGES) -> None:
        self._limit = limit
        self._streak = 0

    def record(self, result: CaseResult) -> None:
        """Track one scored case; raise once the streak passes the limit."""
        self._streak = self._streak + 1 if result.unmeasured else 0
        if self._streak >= self._limit:
            raise UpstreamOutage(
                f"{self._streak} 个用例连续无法连上模型服务，已中止本次运行"
            )


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``queryagent`` console script."""
    parser = argparse.ArgumentParser(prog="queryagent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat = subparsers.add_parser("chat", help="interactive Q&A against the configured database")
    chat.add_argument("--config", default="config.yaml", help="path to config.yaml")
    chat.add_argument("--verbose", action="store_true", help="show the full agent trace")
    chat.add_argument("--max-turns", type=int, default=8)

    chat.add_argument("--no-trace", action="store_true", help="do not record traces")

    ask = subparsers.add_parser("ask", help="one-shot question, scriptable (answer to stdout)")
    ask.add_argument("question", help="natural-language question")
    ask.add_argument("--config", default="config.yaml", help="path to config.yaml")
    ask.add_argument("--verbose", action="store_true", help="show the full agent trace")
    ask.add_argument("--max-turns", type=int, default=8)
    ask.add_argument("--no-trace", action="store_true", help="do not record traces")

    replay = subparsers.add_parser("replay", help="re-render a recorded trace")
    replay.add_argument("path", help="path to a .jsonl trace file")

    evalp = subparsers.add_parser("eval", help="run the eval suite and write a markdown report")
    evalp.add_argument("--config", default="config.yaml", help="path to config.yaml")
    evalp.add_argument("--cases", default="eval/cases.yaml", help="self-built cases YAML")
    evalp.add_argument("--public", help="public subset JSON (overrides --cases)")
    evalp.add_argument("--db-dir", help="databases dir for --public (dir/<db_id>/<db_id>.sqlite)")
    evalp.add_argument("--backend", choices=["anthropic", "openai_compatible"])
    evalp.add_argument("--model", help="override llm.model (dual-model reports, spec §三)")
    evalp.add_argument("--base-url", help="override llm.base_url")
    evalp.add_argument("--output", default="eval_report.md")
    evalp.add_argument(
        "--resume",
        action="store_true",
        help="reuse cases already scored in <output>.partial.jsonl instead of paying again",
    )
    evalp.add_argument("--max-turns", type=int, default=8)

    args = parser.parse_args(argv)
    handlers = {
        "chat": _cmd_chat,
        "ask": _cmd_ask,
        "replay": _cmd_replay,
        "eval": _cmd_eval,
    }
    handler = handlers.get(args.command)
    if handler is None:
        return 2
    try:
        return handler(args)
    except KeyboardInterrupt:
        # Ctrl-C during a slow query is ordinary use, not a crash to report.
        # Resources are released by the commands' own ExitStacks on the way out.
        print("\n[已取消]", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - top level: explain, never dump a traceback
        return _report_error(exc, verbose=getattr(args, "verbose", False))


EXIT_USER_ERROR = 2
EXIT_INTERNAL_DEFECT = 70  # sysexits EX_SOFTWARE
EXIT_TEMPORARY_FAILURE = 75  # sysexits EX_TEMPFAIL


def _report_error(exc: BaseException, *, verbose: bool) -> int:
    """Print one line of problem, one line of fix, and classify the exit code.

    Three classes, because a script and a human need different reactions:
    the user misconfigured something (2), our code is broken (70), or the
    upstream service is having a moment (75, retryable).
    """
    if verbose:
        traceback.print_exc()
    problem, fix, code = _explain(exc)
    print(f"[错误] {problem}", file=sys.stderr)
    if fix:
        print(f"  → {fix}", file=sys.stderr)
    return code


def _is_temporary(exc: BaseException, text: str) -> bool:
    """Kept as a named seam for the CLI; the definition lives in errors."""
    return is_transient(exc)


def _explain(exc: BaseException) -> tuple[str, str, int]:
    """Map a failure to (what went wrong, what to do, exit code)."""
    text = str(exc)
    if isinstance(exc, ImportError):
        missing = getattr(exc, "name", "") or text
        if "clickhouse" in missing:
            return (
                "缺少 ClickHouse 可选驱动。",
                'pip install -e ".[clickhouse]"',
                EXIT_USER_ERROR,
            )
        return (f"缺少依赖：{missing}。", 'pip install -e ".[dev]"', EXIT_USER_ERROR)
    if isinstance(exc, FileNotFoundError):
        return (
            f"找不到文件：{exc.filename or text}。",
            "检查 --config 路径；示例配置在 examples/demo_ecommerce/ 下。",
            EXIT_USER_ERROR,
        )
    for env_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if env_var in text and "not set" in text:
            return (f"{env_var} 未设置。", f"export {env_var}=<你的 key>", EXIT_USER_ERROR)
    if isinstance(exc, ConnectorError) and "not found" in text:
        return (
            f"{text}。",
            "先运行 make demo-data 生成示例库，或修正 config 里的 database.path。",
            EXIT_USER_ERROR,
        )
    if "HTTP 401" in text or "Authentication" in text:
        # A rejected key never fixes itself; retrying is not the answer.
        return (
            "LLM 拒绝了这个 API key（401）。",
            "检查 key 是否有效、是否与 config 里的 backend/base_url 匹配。",
            EXIT_USER_ERROR,
        )
    if _is_temporary(exc, text):
        return (
            f"上游服务暂时不可用：{text[:160]}",
            "稍后重试；持续失败可在 config 里换一个 base_url 或供应商。"
            "（退出码 75 = 可重试，脚本可据此自动重跑）",
            EXIT_TEMPORARY_FAILURE,
        )
    if isinstance(exc, ValueError):
        return (f"配置有问题：{text}", "修正 config.yaml 后重试。", EXIT_USER_ERROR)
    if isinstance(exc, QueryAgentError):
        return (text, "", EXIT_USER_ERROR)
    return (
        f"这是 QueryAgent 自身的缺陷（bug）：{type(exc).__name__}: {text}",
        "请带上 --verbose 的完整调用栈反馈；这不是你能通过改设置解决的问题。",
        EXIT_INTERNAL_DEFECT,
    )


def _make_trace_writer(config: AppConfig, disabled: bool, question: str) -> TraceWriter | None:
    """Build a trace writer unless tracing is off; prunes old traces first."""
    if disabled or not config.trace:
        return None
    directory = Path(TRACE_DIR_NAME)
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
            f"[trace] 已记录到 {writer.path.parent}/ —— 含问题、SQL 与查询结果，"
            "可能包含业务数据；该目录已在 .gitignore 中。"
            "关闭方式：--no-trace 或 config 里 trace: false",
            file=sys.stderr,
        )


def _cmd_replay(args: argparse.Namespace) -> int:
    """Re-render a recorded trace (always full detail — that is the point)."""
    events = read_trace(args.path)
    for event in events:
        _render_event(event, verbose=True)
    skipped = count_trace_lines(args.path) - len(events)
    if skipped > 0:
        # Never hide corruption: a partial tail usually means the run was
        # killed, which is itself part of what the replay should tell you.
        print(
            f"[warn] {skipped} 行无法解析（通常是进程中断留下的残缺尾行），已跳过",
            file=sys.stderr,
        )
    return 0


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
) -> SessionRunQuestion:
    """Wire backend + context + metrics + tools for one data source.

    The backend owns an HTTP client, so its release is registered on the
    caller's stack: a public eval builds one per database, and leaking a
    connection pool per data source is how a long run runs out of sockets.
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
    tools = make_default_tools(
        connector,
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
        connector = make_connector(config.database)
        stack.callback(connector.close)
        run_question = _make_run_question(connector, config, args.max_turns, stack)
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
        connector = make_connector(config.database)
        stack.callback(connector.close)
        run_question = _make_run_question(connector, config, args.max_turns, stack)
        for event in run_question(args.question):
            if writer is not None:
                writer.write(event)
            _render_event(event, args.verbose)
            if isinstance(event, ErrorEvent):
                exit_code = 2
    return exit_code


def _cmd_eval(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if args.backend or args.model or args.base_url:
        # replace() keeps unrelated fields (notably temperature) intact —
        # rebuilding LLMConfig from scratch silently dropped them once.
        config = dataclasses.replace(
            config,
            llm=dataclasses.replace(
                config.llm,
                backend=args.backend or config.llm.backend,
                model=args.model or config.llm.model,
                base_url=args.base_url or config.llm.base_url,
            ),
        )
    source = args.public or args.cases
    signature = (
        f"{config.llm.backend}/{config.llm.model}"
        f" · {Path(source).name} · turns={args.max_turns}"
    )
    try:
        log = ResultLog(
            Path(args.output).with_suffix(".partial.jsonl"),
            resume=args.resume,
            signature=signature,
        )
    except ResumeMismatch as exc:
        print(f"[错误] 无法续跑：{exc}", file=sys.stderr)
        print("  → 删除该 .partial.jsonl 重新开始，或改回原配置。", file=sys.stderr)
        return 2
    try:
        return _run_eval(args, config, log)
    except UpstreamOutage as exc:
        log.close()
        print(f"[错误] {exc}", file=sys.stderr)
        print(
            "  → 这是上游故障，不是测量结果。稍后用 --resume 续跑；"
            "已完成的用例不会重付。",
            file=sys.stderr,
        )
        return EXIT_TEMPORARY_FAILURE


def _run_eval(args: argparse.Namespace, config: AppConfig, log: ResultLog) -> int:
    if args.public:
        if not args.db_dir:
            print("--public requires --db-dir", file=sys.stderr)
            return 2
        # Public benchmarks have no metrics.yaml of their own; the demo's
        # e-commerce metrics must not leak into their prompts.
        public_config = dataclasses.replace(config, metrics_path=None)
        try:
            results = _eval_public(
                args.public, Path(args.db_dir), public_config, args.max_turns, log
            )
        finally:
            log.close()
        title = "QueryAgent Eval Report — public subset"
    else:
        try:
            results = _eval_self_built(args.cases, config, args.max_turns, log)
        finally:
            log.close()
        title = "QueryAgent Eval Report — self-built cases"
    report = render_report(results, title=title, model_label=config.llm.model)
    output = Path(args.output)
    # Never lose a finished (paid-for) run to a missing folder.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    passed = sum(1 for r in results if r.passed)
    print(f"{passed}/{len(results)} cases passed; report -> {args.output}")
    return 0 if passed == len(results) else 3


def _record(
    result: CaseResult,
    results: list[CaseResult],
    log: ResultLog,
    guard: _OutageGuard,
) -> None:
    """Collect one result, persisting it only if it was actually measured.

    An unmeasured case must be retried on the next run, so writing it to the
    resume log would bake the outage into the final number.
    """
    results.append(result)
    if not result.unmeasured:
        log.append(result)
    guard.record(result)


def _eval_self_built(
    cases_path: str, config: AppConfig, max_turns: int, log: ResultLog
) -> list[CaseResult]:
    cases = load_cases(cases_path)
    done = log.completed()
    guard = _OutageGuard()
    with contextlib.ExitStack() as stack:
        connector = make_connector(config.database)
        stack.callback(connector.close)
        run_question = _make_run_question(connector, config, max_turns, stack)
        results = []
        for case in cases:
            if case.id in done:
                results.append(done[case.id])
                continue
            result = run_case(case, run_question=run_question, connector=connector)
            _record(result, results, log, guard)
        return results


def _eval_public(
    subset_path: str, db_dir: Path, config: AppConfig, max_turns: int, log: ResultLog
) -> list[CaseResult]:
    """Public-benchmark mode: one SQLite database (and runtime) per db_id."""
    cases = load_subset(subset_path)
    done = log.completed()
    guard = _OutageGuard()
    results: list[CaseResult] = []
    by_db: dict[str, list[EvalCase]] = {}
    for case in cases:
        by_db.setdefault(case.db_id, []).append(case)
    for db_id, db_cases in by_db.items():
        try:
            connector = SQLiteConnector(path=str(db_dir / db_id / f"{db_id}.sqlite"))
        except Exception as exc:  # noqa: BLE001
            # One unusable database costs its own cases, not the whole run —
            # a public suite is 30 paid minutes and must survive to a report.
            reason = f"database '{db_id}' unusable: {exc}"
            print(f"[warn] {reason}", file=sys.stderr)
            for case in db_cases:
                if case.id in done:
                    results.append(done[case.id])
                    continue
                _record(unscoreable_case(case, reason), results, log, guard)
            continue
        try:
            with contextlib.ExitStack() as stack:
                stack.callback(connector.close)
                run_question = _make_run_question(connector, config, max_turns, stack)
                for case in db_cases:
                    if case.id in done:
                        results.append(done[case.id])
                        continue
                    result = run_case(case, run_question=run_question, connector=connector)
                    _record(result, results, log, guard)
        except UpstreamOutage:
            raise
        except Exception as exc:  # noqa: BLE001
            reason = f"database '{db_id}' aborted: {type(exc).__name__}: {exc}"
            print(f"[warn] {reason}", file=sys.stderr)
            recorded = {r.case.id for r in results}
            for case in db_cases:
                if case.id in recorded:
                    continue
                result = unscoreable_case(case, reason)
                log.append(result)
                results.append(result)
    results.sort(key=lambda r: r.case.id)
    return results


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


if __name__ == "__main__":
    raise SystemExit(main())
