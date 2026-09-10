"""QueryAgent CLI: ``chat`` (interactive, multi-turn), ``ask`` (one-shot),
``eval`` (scored suites) — all pure consumers of the AgentEvent stream —
plus ``flow``, which is not.

``flow`` drives the trusted workflow layer instead: it prepares a 口径, shows
it, requires an explicit confirmation, and only then executes a
maintainer-declared query. It shares no execution path with ``ask``/``chat``;
that is the point of it (docs/specs/workflow-slice-1a-2026-09.md).

``--verbose`` renders the full THINK/ACT/OBSERVE trace; the default shows
answers only. In chat, a ClarifyEvent renders the agent's question, folds
the user's reply back into the pending question and re-runs; answered turns
are kept as session conversation so follow-ups can refer back.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import os
import sys
import threading
import traceback
import uuid
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from queryagent.agent import run_agent
from queryagent.config import AppConfig, load_config
from queryagent.connectors import make_connector
from queryagent.connectors.base import Connector
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.context import ContextBuilder
from queryagent.errors import ConnectorError, QueryAgentError, is_transient
from queryagent.evals.cases import EvalCase, load_cases
from queryagent.evals.checkpoint import ResultLog, ResumeMismatch
from queryagent.evals.identity import run_signature
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
from queryagent.knowledge.embedding import EmbeddingClient
from queryagent.knowledge.index import SqliteKnowledgeIndex
from queryagent.knowledge.provider import LocalKnowledgeProvider, scope_of
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
from queryagent.workflow.builder import VARIANT_RULE_KEY, MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.errors import (
    ConfirmationRequired,
    MappingNotFound,
    PermissionDenied,
    StaleVersion,
    WorkflowError,
)
from queryagent.workflow.evidence_builder import CompositeDraftBuilder, EvidenceDraftBuilder
from queryagent.workflow.execution import make_connector_executor
from queryagent.workflow.mappings import load_mappings
from queryagent.workflow.models import (
    CONFLICT_SEPARATOR,
    PERIOD_RULE_KEY,
    ActorContext,
    Candidate,
    DefinitionDraft,
    DraftStatus,
    Rule,
    RuleSource,
)
from queryagent.workflow.periods import PeriodError, find_period, parse_period
from queryagent.workflow.render import (
    render_definition_summary,
    render_draft,
    render_unenforced,
    rule_label,
)
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

_trace_notice_shown = False

# Consecutive cases lost to an unreachable provider before a run gives up.
# Burning a 200-case suite against a dead endpoint produces a report that
# reads like a measurement of 0%; stopping early keeps it honest and, thanks
# to checkpointing, costs nothing to resume.
MAX_CONSECUTIVE_OUTAGES = 5

# Chat turns kept in memory. The prompt side is already trimmed by the
# context budget; this bounds the session's own list, which otherwise grew
# for as long as the session lived.
MAX_REMEMBERED_TURNS = 20


class UpstreamOutage(Exception):
    """Too many consecutive cases went unmeasured.

    Carries the last case's reason so the exit code can match the cause: a
    provider outage is worth retrying, an exhausted balance or a rejected key
    is not, and telling a retry loop otherwise makes it spin forever.
    """

    def __init__(self, message: str, *, reason: str, retryable: bool) -> None:
        super().__init__(message)
        self.reason = reason
        self.retryable = retryable


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
                f"{self._streak} 个用例连续未能测量，已中止本次运行"
                f"（最后一次：{result.failure_reason[:160]}）",
                reason=result.failure_reason,
                retryable=result.retryable,
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

    flow = subparsers.add_parser(
        "flow", help="confirmation-gated query: show the 口径, confirm it, then execute"
    )
    flow.add_argument("question", help="natural-language question")
    flow.add_argument("--config", default="config.yaml", help="path to config.yaml")
    flow.add_argument("--subject", default=os.environ.get("USER", "local"), help="acting user id")
    flow.add_argument("--workspace", default="default", help="business workspace id")
    flow.add_argument(
        "--variant", help="pick a 口径 non-interactively (still requires --yes to execute)"
    )
    flow.add_argument(
        "--adopt",
        action="append",
        default=[],
        metavar="KEY:N",
        help="where documents disagree, adopt one reading non-interactively "
        "(e.g. counting_basis:0); recorded as 本次约定, citing that document",
    )
    flow.add_argument(
        "--rule",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="state a rule the 口径 requires but nothing has stated yet "
        "(e.g. time_window=按自然月统计); recorded as 本次约定",
    )
    flow.add_argument(
        "--period",
        help="the statistical period, if the question does not state one or you "
        "want a different one (e.g. 上个月, 2026-08-01..2026-08-31); recorded as 本次约定",
    )
    flow.add_argument(
        "--yes",
        action="store_true",
        help="confirm the 口径 without prompting. The confirmation record is still "
        "created server-side and bound to this exact version — this flag automates "
        "the human, it does not bypass the gate.",
    )

    kb = subparsers.add_parser("kb", help="build and inspect the document evidence index")
    kb.add_argument("kb_action", choices=["import", "list"], help="what to do")
    kb.add_argument("--config", default="config.yaml", help="path to config.yaml")
    kb.add_argument("--workspace", help="list only this business workspace")

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
        "--data-version", help="immutable server data snapshot ID; required to resume"
    )
    evalp.add_argument(
        "--resume",
        action="store_true",
        help="reuse cases already scored in <output>.partial.jsonl instead of paying again",
    )
    evalp.add_argument("--max-turns", type=int, default=8)
    evalp.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="run this many cases at once (default 1). Higher values finish "
        "sooner but push harder against provider rate limits.",
    )

    args = parser.parse_args(argv)
    handlers = {
        "chat": _cmd_chat,
        "ask": _cmd_ask,
        "flow": _cmd_flow,
        "kb": _cmd_kb,
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


def _workflow_fix(exc: WorkflowError) -> str:
    """Who can actually resolve this refusal."""
    if isinstance(exc, MappingNotFound):
        return (
            "这是维护者的工作：在 workflow.mappings_path 指向的映射文件里为该口径"
            "声明经过评审的 SQL。系统不会自行猜测查询。"
        )
    if isinstance(exc, StaleVersion):
        return "口径已被改动。重新查看当前版本的确认单，再确认一次。"
    if isinstance(exc, ConfirmationRequired):
        return "先确认口径再执行；未确认或已失效的口径不会执行任何查询。"
    if isinstance(exc, PermissionDenied):
        return "当前身份没有该对象的访问权限。"
    return "查看上面的说明后重试。"


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
        if "pypdf" in missing:
            return (
                "缺少 PDF 可选驱动；Markdown 与 DOCX 不需要它。",
                'pip install -e ".[docs]"',
                EXIT_USER_ERROR,
            )
        return (f"缺少依赖：{missing}。", 'pip install -e ".[dev]"', EXIT_USER_ERROR)
    if isinstance(exc, FileNotFoundError):
        return (
            f"找不到文件：{exc.filename or text}。",
            "检查 --config 路径；示例配置在 examples/demo_ecommerce/ 下。",
            EXIT_USER_ERROR,
        )
    for env_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "QUERYAGENT_EMBEDDING_API_KEY"):
        if env_var in text and "not set" in text:
            return (f"{env_var} 未设置。", f"export {env_var}=<你的 key>", EXIT_USER_ERROR)
    if isinstance(exc, WorkflowError):
        # A refusal from the trusted layer is the system working, not failing.
        # Each refusal has a different person who can act on it, so generic
        # "try again" advice would send every one of them to the wrong place.
        return (text, _workflow_fix(exc), EXIT_USER_ERROR)
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


def _cmd_kb(args: argparse.Namespace) -> int:
    """Build or inspect the document index.

    Import prints every file it took in *and* every file it could not read.
    A document missing from the index is a set of business rules silently
    absent from every future draft, and the operator is the only person in a
    position to notice (K8).
    """
    config = load_config(args.config)
    if not config.knowledge.enabled:
        raise ValueError(
            "配置里没有 knowledge.sources；文档证据未启用，flow 仍按 metrics.yaml 生成草案"
        )
    with contextlib.ExitStack() as stack:
        index = SqliteKnowledgeIndex(config.knowledge.index_path)
        stack.callback(index.close)
        if args.kb_action == "import":
            # Built before importing anything, so a missing key fails before
            # work is done rather than after half the sources are indexed.
            embedder = _make_embedder(config)
            for source in config.knowledge.sources:
                print(f"[{source.workspace}] {source.path}")
                print(index.import_directory(source.path, workspace_id=source.workspace).render())
                if embedder is not None and config.knowledge.embedding is not None:
                    added = index.embed_missing(source.workspace, embedder)
                    # Said out loud: this is the moment document text leaves
                    # the machine.
                    print(
                        f"  语义向量：新增 {added} 个（正文已发送至 "
                        f"{config.knowledge.embedding.base_url}；已有向量不重复发送）"
                    )
            return 0
        workspaces = (
            [args.workspace]
            if args.workspace
            else sorted({source.workspace for source in config.knowledge.sources})
        )
        for workspace in workspaces:
            chunks = index.chunks_in(workspace)
            print(f"[{workspace}] {len(chunks)} 个片段")
            for chunk in chunks:
                print(f"  · {chunk.citation()}")
                print(f"      {chunk.text[:60]}")
        return 0


def _make_embedder(config: AppConfig) -> EmbeddingClient | None:
    embedding = config.knowledge.embedding
    if embedding is None:
        return None
    return EmbeddingClient(model=embedding.model, base_url=embedding.base_url)


def _knowledge_provider(index: SqliteKnowledgeIndex, config: AppConfig) -> LocalKnowledgeProvider:
    """Keyword unless ``knowledge.embedding`` is configured."""
    embedder = _make_embedder(config)
    embedding = config.knowledge.embedding
    if embedder is None or embedding is None or embedding.min_similarity is None:
        return LocalKnowledgeProvider(index, embedder)
    return LocalKnowledgeProvider(index, embedder, min_similarity=embedding.min_similarity)


def _cmd_flow(args: argparse.Namespace) -> int:
    """Prepare a 口径, require an explicit confirmation, then execute it.

    Exit codes: 0 executed, 2 refused or declined. A decline is not an error
    in the CLI sense but it is a non-zero outcome, because a script that
    treats "the user said no" as success is a script that will eventually
    report a number nobody approved.
    """
    config = load_config(args.config)
    if not config.metrics_path:
        raise ValueError(
            "flow needs declared business metrics; set metrics_path in the config file"
        )
    if not config.workflow.mappings_path:
        raise ValueError(
            "flow needs a maintainer mapping file; set workflow.mappings_path in the config "
            "file (see examples/query_mappings.yaml)"
        )
    actor = ActorContext(subject_id=args.subject, workspace_id=args.workspace)
    today = _today(config)

    with contextlib.ExitStack() as stack:
        connector = make_connector(config.database)
        stack.callback(connector.close)
        store = SqliteWorkflowStore(config.workflow.state_path)
        stack.callback(store.close)
        provider = None
        evidence = None
        if config.knowledge.enabled:
            index = SqliteKnowledgeIndex(config.knowledge.index_path)
            stack.callback(index.close)
            provider = _knowledge_provider(index, config)
            if provider.is_semantic and not index.vectors_in(actor.workspace_id):
                # K10: the provider falls back to keyword on an un-embedded
                # corpus. Legitimate — but not silently.
                print(
                    "[提示] 已配置语义检索，但该业务空间尚无向量；本次按关键词检索。"
                    "运行 queryagent kb import 生成向量。",
                    file=sys.stderr,
                )
            evidence = EvidenceDraftBuilder(
                provider,
                make_backend(config.llm),
                required_keys=(),  # gaps come from the maintainer metric, not extraction
            )
        workflow = QueryWorkflow(
            store=store,
            builder=CompositeDraftBuilder(
                MetricDraftBuilder(
                    YamlMetricStore(config.metrics_path), today=lambda: today
                ),
                evidence,
            ),
            compiler=TemplateCompiler(
                load_mappings(config.workflow.mappings_path), dialect=connector.dialect
            ),
            executor=make_connector_executor(
                connector,
                timeout_s=config.safety.timeout_s,
                max_rows=config.safety.max_rows,
            ),
            ref_checker=provider,
        )
        known = {source.workspace for source in config.knowledge.sources}
        if provider is not None and actor.workspace_id not in known:
            # Retrieving nothing because the workspace does not exist looks
            # exactly like the documents being silent, and the second is a
            # claim about the business. Say which it is.
            print(
                f"[提示] 业务空间 '{actor.workspace_id}' 没有配置任何文档来源"
                f"（已配置：{', '.join(sorted(known))}）；本次不会有文档依据。",
                file=sys.stderr,
            )
        return _run_flow(workflow, actor, args, provider, today)


def _run_flow(
    workflow: QueryWorkflow,
    actor: ActorContext,
    args: argparse.Namespace,
    provider: LocalKnowledgeProvider | None = None,
    today: date | None = None,
) -> int:
    request_id = uuid.uuid4().hex
    today = today or date.today()
    draft = workflow.prepare(actor, args.question, request_id=request_id)
    if args.period:
        # Stated on purpose, it replaces whatever the question's words gave.
        draft = workflow.amend(
            actor,
            draft.draft_id,
            expected_version=draft.version,
            rules=(_stated_period(args.period, today),),
        )
    if PERIOD_RULE_KEY in draft.definition.missing:
        _explain_missing_period(args.question, today)
    citations = _citations(provider, actor, args.question)
    cited = tuple(
        rule.evidence_ref for rule in draft.definition.rules if rule.evidence_ref
    ) + tuple(c.evidence_ref for c in draft.definition.candidates if c.evidence_ref)
    if cited:
        workflow.attach_evidence(actor, draft.draft_id, cited)
    print(render_draft(draft, citations))
    if provider is not None and not citations:
        print("\n（未检索到该身份可见的相关文档；以下口径仅来自系统映射）")

    if draft.status is DraftStatus.NEEDS_INPUT:
        rules = _open_choices(draft, args, citations, today)
        if rules is None:
            print("\n[已取消] 未选择口径，没有执行任何查询。")
            return 2
        if rules:
            draft = workflow.amend(
                actor, draft.draft_id, expected_version=draft.version, rules=rules
            )
            print()
            print(render_draft(draft, citations))

    if not args.yes and not _prompt_confirm():
        print("\n[已取消] 未确认口径，没有执行任何查询。")
        return 2

    confirmation = workflow.confirm(
        actor, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    run = workflow.execute(actor, confirmation.confirmation_id, idempotency_key=request_id)
    print()
    print(f"结果（执行口径：{render_definition_summary(draft.definition)}）")
    print("  " + " | ".join(run.columns))
    for row in run.rows:
        print("  " + " | ".join("NULL" if v is None else str(v) for v in row))
    if run.truncated:
        print("  （结果已在行数上限处截断）")
    unenforced = render_unenforced(draft.definition)
    if unenforced:
        print(f"  （{unenforced}）")
    print(f"\n执行的 SQL（维护者映射 {draft.definition.metric}）：\n  {run.sql}")
    return 0


def _citations(
    provider: LocalKnowledgeProvider | None, actor: ActorContext, question: str
) -> dict[str, str]:
    """Human-readable locations for whatever this identity can actually see.

    Retrieval is scoped, so a document in another workspace simply is not in
    the result — there is nothing to redact afterwards.
    """
    if provider is None:
        return {}
    hits = provider.search(scope_of(actor), question, limit=8)
    return {f"{hit.ref.doc_id}#{hit.ref.chunk_id}": hit.chunk.citation() for hit in hits}


def _today(config: AppConfig) -> date:
    """Today in the configured business time zone — what 「上个月」 is relative to."""
    return datetime.now(ZoneInfo(config.workflow.timezone)).date()


def _stated_period(text: str, today: date) -> Rule:
    """A period the user stated on purpose, parsed exactly as a question's would be.

    Raises PeriodError (a ValueError) when it cannot be read: a period that
    was typed but not understood must not quietly become no period at all.
    """
    period = parse_period(text, today)
    return Rule(PERIOD_RULE_KEY, period.encode(), RuleSource.USER, note=f"由「{text}」换算")


def _explain_missing_period(question: str, today: date) -> None:
    """Say why the question's own time words did not become a period."""
    try:
        find_period(question, today)
    except PeriodError as exc:
        print(f"[提示] {exc}", file=sys.stderr)


def _prompt_period() -> str:
    try:
        return input(
            "\n「统计区间」尚未确定。写下要统计的时间"
            "（如 上个月、2026-08-01..2026-08-31；回车取消）： "
        ).strip()
    except EOFError:
        return ""


def _open_choices(
    draft: DefinitionDraft,
    args: argparse.Namespace,
    citations: dict[str, str],
    today: date,
) -> tuple[Rule, ...] | None:
    """The user's answer to every open choice, or None when they decline.

    Document disagreements are asked first, then rules nothing has stated,
    then the executable variant: which handbook the user sides with, and what
    they take the gaps to mean, is what they need before picking what runs.
    The two answers are not checked against each other — the system cannot
    tell what a handbook sentence means — which is why the whole sheet is
    printed again before the final confirmation (D05).
    """
    definition = draft.definition
    disagreements = {
        key: [c for c in definition.candidates if c.rule_key == key]
        for key in definition.missing
        if key != VARIANT_RULE_KEY
    }
    disagreements = {key: options for key, options in disagreements.items() if options}
    valid = {c.key for options in disagreements.values() for c in options}
    unknown = [value for value in args.adopt if value not in valid]
    if unknown:
        raise ValueError(
            f"未知的文档取法：{', '.join(unknown)}；当前可采用："
            f"{', '.join(sorted(valid)) or '（没有文档分歧）'}"
        )
    gaps = [
        key for key in definition.missing if key != VARIANT_RULE_KEY and key not in disagreements
    ]
    supplied: dict[str, str] = {}
    for item in args.rule:
        key, sep, value = item.partition("=")
        if not sep or not value.strip():
            raise ValueError(
                f"--rule 需要写成 KEY=取值，例如 time_window=按自然月统计；收到：{item!r}"
            )
        supplied[key.strip()] = value.strip()
    stray = sorted(set(supplied) - set(gaps))
    if stray:
        raise ValueError(
            f"这些规则没有待补的缺口：{', '.join(stray)}；当前待补：{', '.join(gaps) or '（无）'}"
        )
    rules: list[Rule] = []
    for rule_key, options in disagreements.items():
        chosen_key = next(
            (value for value in args.adopt if value.split(CONFLICT_SEPARATOR, 1)[0] == rule_key),
            "",
        ) or _prompt_adopt(rule_label(rule_key), options)
        if not chosen_key:
            return None
        chosen = next((c for c in options if c.key == chosen_key), None)
        if chosen is None:
            raise ValueError(
                f"「{rule_label(rule_key)}」没有取法 '{chosen_key}'；"
                f"可选：{', '.join(c.key for c in options)}"
            )
        # The words are the handbook's, the decision is the user's (D07): a
        # 本次约定 rule that keeps the adopted document's citation.
        rules.append(
            Rule(
                rule_key,
                chosen.summary,
                RuleSource.USER,
                evidence_ref=chosen.evidence_ref,
                note="采用文档写法",
            )
        )
    for key in gaps:
        if key == PERIOD_RULE_KEY:
            text = args.period or supplied.get(key) or _prompt_period()
            if not text:
                return None
            rules.append(_stated_period(text, today))
            continue
        # Nothing states this rule and nothing may default it: the user writes
        # it down, and it is marked as theirs (D07).
        value = supplied.get(key) or _prompt_rule(rule_label(key))
        if not value:
            return None
        rules.append(Rule(key, value, RuleSource.USER))
    if VARIANT_RULE_KEY in definition.missing:
        variants = {c.key for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY}
        choice = args.variant or _prompt_variant(draft)
        if not choice:
            return None
        if choice not in variants:
            raise ValueError(f"未知口径 '{choice}'；可选：{', '.join(sorted(variants))}")
        rules.append(Rule(VARIANT_RULE_KEY, choice, RuleSource.USER))
    return tuple(rules)


def _prompt_rule(label: str) -> str:
    try:
        return input(f"\n「{label}」尚未写明，维护者要求写明。写下本次约定（回车取消）： ").strip()
    except EOFError:
        return ""


def _prompt_adopt(label: str, options: list[Candidate]) -> str:
    keys = ", ".join(c.key for c in options)
    try:
        return input(f"\n「{label}」文档之间有分歧，采用哪一种写法 [{keys}]（回车取消）： ").strip()
    except EOFError:
        return ""


def _prompt_variant(draft: DefinitionDraft) -> str:
    keys = ", ".join(
        c.key for c in draft.definition.candidates if c.rule_key == VARIANT_RULE_KEY
    )
    try:
        return input(f"\n选择口径 [{keys}]（回车取消）： ").strip()
    except EOFError:
        return ""


def _prompt_confirm() -> bool:
    try:
        return input("\n确认按以上口径执行？[y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


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
    if args.public and not args.db_dir:
        print("--public requires --db-dir", file=sys.stderr)
        return 2
    if (
        args.resume
        and not args.public
        and config.database.type != "sqlite"
        and not args.data_version
    ):
        print("--resume on a server database requires --data-version", file=sys.stderr)
        return 2
    signature = run_signature(
        config,
        Path(args.public or args.cases),
        max_turns=args.max_turns,
        db_dir=Path(args.db_dir) if args.public else None,
        data_version=args.data_version,
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
        if exc.retryable:
            print(
                "  → 这是上游故障，不是测量结果。稍后用 --resume 续跑；"
                "已完成的用例不会重付。",
                file=sys.stderr,
            )
            return EXIT_TEMPORARY_FAILURE
        print(
            "  → 服务方拒绝了请求（余额、配额或 key 的问题），重试不会好转。"
            "处理后用 --resume 续跑；已完成的用例不会重付。",
            file=sys.stderr,
        )
        return EXIT_USER_ERROR


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
                args.public,
                Path(args.db_dir),
                public_config,
                args.max_turns,
                log,
                args.concurrency,
            )
        finally:
            log.close()
        title = "QueryAgent Eval Report — public subset"
    else:
        try:
            results = _eval_self_built(
                args.cases, config, args.max_turns, log, args.concurrency
            )
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
    return 0 if all(r.passed and r.completed is True for r in results) else 3


class _WorkerPool:
    """One connector and one wired runner per thread.

    SQLite connections cannot be shared between threads, and a per-thread
    backend keeps one slow call from blocking another. Everything created
    here is closed by the caller's ExitStack.
    """

    def __init__(
        self,
        build: Callable[[contextlib.ExitStack], tuple[Connector, SessionRunQuestion]],
        stack: contextlib.ExitStack,
    ) -> None:
        self._build = build
        self._stack = stack
        self._local = threading.local()
        self._lock = threading.Lock()

    def get(self) -> tuple[Connector, SessionRunQuestion]:
        """The calling thread's worker, built on first use."""
        worker = getattr(self._local, "worker", None)
        if worker is None:
            with self._lock:  # ExitStack registration is not thread-safe
                worker = self._build(self._stack)
            self._local.worker = worker
        return worker


def _run_batch(
    cases: Sequence[EvalCase],
    *,
    pool: _WorkerPool,
    done: dict[str, CaseResult],
    results: list[CaseResult],
    log: ResultLog,
    guard: _OutageGuard,
    concurrency: int,
) -> None:
    """Score ``cases``, in order, optionally several at a time.

    Completed cases are persisted by one writer immediately. The caller sorts
    the report later. Outage streaks follow completion order; at most
    ``concurrency`` cases are in flight, and these are drained on an outage.
    """
    pending = [case for case in cases if case.id not in done]
    for case in cases:
        if case.id in done:
            results.append(done[case.id])

    def score(case: EvalCase) -> CaseResult:
        connector, run_question = pool.get()
        return run_case(case, run_question=run_question, connector=connector)

    if concurrency <= 1:
        for case in pending:
            _record(score(case), results, log, guard)
        return
    remaining = iter(pending)
    outage: UpstreamOutage | None = None
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        active = {
            executor.submit(score, case)
            for case in [next(remaining, None) for _ in range(concurrency)]
            if case is not None
        }
        try:
            while active:
                finished, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in finished:
                    result = future.result()
                    if outage is not None:
                        # Preserve paid-for in-flight results without restarting the run.
                        results.append(result)
                        if not result.unmeasured:
                            log.append(result)
                    else:
                        try:
                            _record(result, results, log, guard)
                        except UpstreamOutage as exc:
                            outage = exc
                    active.remove(future)
                if outage is None:
                    for _ in range(concurrency - len(active)):
                        next_case = next(remaining, None)
                        if next_case is None:
                            break
                        active.add(executor.submit(score, next_case))
        except KeyboardInterrupt:
            # Stop admission, drain the bounded in-flight set, and preserve even
            # results that completed just before Ctrl-C interrupted the writer.
            log.close()
            recovered = ResultLog(log.path, resume=True, signature=log.signature)
            saved = recovered.completed()
            try:
                for future in active:
                    result = future.result()
                    if not result.unmeasured and result.case.id not in saved:
                        recovered.append(result)
            finally:
                recovered.close()
            raise

    if outage is not None:
        raise outage


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
    cases_path: str,
    config: AppConfig,
    max_turns: int,
    log: ResultLog,
    concurrency: int = 1,
) -> list[CaseResult]:
    cases = load_cases(cases_path)
    done = log.completed()
    guard = _OutageGuard()
    results: list[CaseResult] = []
    with contextlib.ExitStack() as stack:
        pool = _WorkerPool(
            lambda st: _build_worker(config, max_turns, st), stack
        )
        _run_batch(
            cases,
            pool=pool,
            done=done,
            results=results,
            log=log,
            guard=guard,
            concurrency=concurrency,
        )
    results.sort(key=lambda r: [c.id for c in cases].index(r.case.id))
    return results


def _build_worker(
    config: AppConfig, max_turns: int, stack: contextlib.ExitStack
) -> tuple[Connector, SessionRunQuestion]:
    """A connector plus its wired runner, both released by ``stack``."""
    connector = make_connector(config.database)
    stack.callback(connector.close)
    return connector, _make_run_question(connector, config, max_turns, stack)


def _eval_public(
    subset_path: str,
    db_dir: Path,
    config: AppConfig,
    max_turns: int,
    log: ResultLog,
    concurrency: int = 1,
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
            db_path = str(db_dir / db_id / f"{db_id}.sqlite")
            # Opened once up front so an unusable database fails fast, before
            # any worker or paid call; workers open their own below.
            connector = SQLiteConnector(path=db_path)
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
                def build(
                    st: contextlib.ExitStack, path: str = db_path
                ) -> tuple[Connector, SessionRunQuestion]:
                    """A fresh connector per worker.

                    Sharing one would let concurrent queries strip each
                    other's timeout: SQLite's deadline guard is installed on
                    the connection, not the statement.
                    """
                    worker_connector = SQLiteConnector(path=path)
                    st.callback(worker_connector.close)
                    return worker_connector, _make_run_question(
                        worker_connector, config, max_turns, st
                    )

                pool = _WorkerPool(build, stack)
                _run_batch(
                    db_cases,
                    pool=pool,
                    done=done,
                    results=results,
                    log=log,
                    guard=guard,
                    concurrency=concurrency,
                )
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
