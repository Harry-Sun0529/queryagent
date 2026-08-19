"""QueryAgent CLI: ``chat`` (interactive, multi-turn), ``ask`` (one-shot),
``eval`` (scored suites) — all pure consumers of the AgentEvent stream.

``--verbose`` renders the full THINK/ACT/OBSERVE trace; the default shows
answers only. In chat, a ClarifyEvent renders the agent's question, folds
the user's reply back into the pending question and re-runs; answered turns
are kept as session conversation so follow-ups can refer back.
"""

from __future__ import annotations

import argparse
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
from queryagent.errors import ConnectorError, QueryAgentError
from queryagent.evals.cases import EvalCase, load_cases
from queryagent.evals.public import load_subset
from queryagent.evals.runner import CaseResult, render_report, run_case
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
    new_trace_path,
    prune_traces,
    read_trace,
)

_trace_notice_shown = False


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
    except Exception as exc:  # noqa: BLE001 - top level: explain, never dump a traceback
        return _report_error(exc, verbose=getattr(args, "verbose", False))


def _report_error(exc: BaseException, *, verbose: bool) -> int:
    """Turn an exception into one line of problem and one line of fix."""
    if verbose:
        traceback.print_exc()
    problem, fix = _explain(exc)
    print(f"[错误] {problem}", file=sys.stderr)
    if fix:
        print(f"  → {fix}", file=sys.stderr)
    return 2


def _explain(exc: BaseException) -> tuple[str, str]:
    """Map a known failure to (what went wrong, what to do about it)."""
    text = str(exc)
    if isinstance(exc, ImportError):
        missing = getattr(exc, "name", "") or text
        if "clickhouse" in missing:
            return (
                "缺少 ClickHouse 可选驱动。",
                'pip install -e ".[clickhouse]"',
            )
        return (f"缺少依赖：{missing}。", 'pip install -e ".[dev]"')
    if isinstance(exc, FileNotFoundError):
        return (
            f"找不到文件：{exc.filename or text}。",
            "检查 --config 路径；示例配置在 examples/demo_ecommerce/ 下。",
        )
    for env_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if env_var in text and "not set" in text:
            return (f"{env_var} 未设置。", f"export {env_var}=<你的 key>")
    if isinstance(exc, ConnectorError) and "not found" in text:
        return (
            f"{text}。",
            "先运行 make demo-data 生成示例库，或修正 config 里的 database.path。",
        )
    if "HTTP 401" in text or "Authentication" in text:
        return (
            "LLM 拒绝了这个 API key（401）。",
            "检查 key 是否有效、是否与 config 里的 backend/base_url 匹配。",
        )
    if isinstance(exc, ValueError):
        return (f"配置有问题：{text}", "修正 config.yaml 后重试。")
    if isinstance(exc, QueryAgentError):
        return (text, "")
    return (f"{type(exc).__name__}: {text}", "加 --verbose 可看完整调用栈。")


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
    for event in read_trace(args.path):
        _render_event(event, verbose=True)
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
    connector: Connector, config: AppConfig, max_turns: int
) -> SessionRunQuestion:
    """Wire backend + context + metrics + tools for one data source."""
    backend = make_backend(config.llm)
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
    connector = make_connector(config.database)
    conversation: list[Message] = []
    try:
        run_question = _make_run_question(connector, config, args.max_turns)
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
    finally:
        connector.close()
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
    connector = make_connector(config.database)
    writer = _make_trace_writer(config, args.no_trace, args.question)
    exit_code = 0
    try:
        run_question = _make_run_question(connector, config, args.max_turns)
        for event in run_question(args.question):
            if writer is not None:
                writer.write(event)
            _render_event(event, args.verbose)
            if isinstance(event, ErrorEvent):
                exit_code = 2
    finally:
        _finish_trace(writer)
        connector.close()
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
    if args.public:
        if not args.db_dir:
            print("--public requires --db-dir", file=sys.stderr)
            return 2
        # Public benchmarks have no metrics.yaml of their own; the demo's
        # e-commerce metrics must not leak into their prompts.
        public_config = dataclasses.replace(config, metrics_path=None)
        results = _eval_public(args.public, Path(args.db_dir), public_config, args.max_turns)
        title = "QueryAgent Eval Report — public subset"
    else:
        results = _eval_self_built(args.cases, config, args.max_turns)
        title = "QueryAgent Eval Report — self-built cases"
    report = render_report(results, title=title, model_label=config.llm.model)
    Path(args.output).write_text(report, encoding="utf-8")
    passed = sum(1 for r in results if r.passed)
    print(f"{passed}/{len(results)} cases passed; report -> {args.output}")
    return 0 if passed == len(results) else 3


def _eval_self_built(
    cases_path: str, config: AppConfig, max_turns: int
) -> list[CaseResult]:
    cases = load_cases(cases_path)
    connector = make_connector(config.database)
    try:
        run_question = _make_run_question(connector, config, max_turns)
        return [
            run_case(case, run_question=run_question, connector=connector) for case in cases
        ]
    finally:
        connector.close()


def _eval_public(
    subset_path: str, db_dir: Path, config: AppConfig, max_turns: int
) -> list[CaseResult]:
    """Public-benchmark mode: one SQLite database (and runtime) per db_id."""
    cases = load_subset(subset_path)
    results: list[CaseResult] = []
    by_db: dict[str, list[EvalCase]] = {}
    for case in cases:
        by_db.setdefault(case.db_id, []).append(case)
    for db_id, db_cases in by_db.items():
        connector = SQLiteConnector(path=str(db_dir / db_id / f"{db_id}.sqlite"))
        try:
            run_question = _make_run_question(connector, config, max_turns)
            for case in db_cases:
                results.append(run_case(case, run_question=run_question, connector=connector))
        finally:
            connector.close()
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
