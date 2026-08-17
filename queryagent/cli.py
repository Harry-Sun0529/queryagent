"""QueryAgent CLI (spec §三 v0.1.1): ``queryagent chat --config config.yaml``.

A pure consumer of the AgentEvent stream — ``--verbose`` renders the full
THINK/ACT/OBSERVE trace, the default shows answers only.

The ClarifyEvent branch below is the reserved seam for v0.2.0: when the agent
asks a clarifying question, the CLI renders it, reads the user's reply and
continues the conversation. The exact continuation mechanism (re-run with an
augmented question, below) is a placeholder to be finalised together with the
human's v0.2.0 agent design.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

from queryagent.agent import run_agent
from queryagent.config import AppConfig, LLMConfig, load_config
from queryagent.connectors import make_connector
from queryagent.connectors.base import Connector
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.context import ContextBuilder
from queryagent.evals.cases import EvalCase, load_cases
from queryagent.evals.public import load_subset
from queryagent.evals.runner import CaseResult, RunQuestion, render_report, run_case
from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    RetryEvent,
    ThinkEvent,
    ToolCallEvent,
)
from queryagent.llm import make_backend
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.schema import render_schema
from queryagent.tools import ToolRegistry, make_clarify_tool, make_default_tools


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``queryagent`` console script."""
    parser = argparse.ArgumentParser(prog="queryagent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat = subparsers.add_parser("chat", help="interactive Q&A against the configured database")
    chat.add_argument("--config", default="config.yaml", help="path to config.yaml")
    chat.add_argument("--verbose", action="store_true", help="show the full agent trace")
    chat.add_argument("--max-turns", type=int, default=8)

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
    if args.command == "chat":
        return _cmd_chat(args)
    if args.command == "eval":
        return _cmd_eval(args)
    return 2


def _make_run_question(
    connector: Connector, config: AppConfig, max_turns: int
) -> RunQuestion:
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

    def run_question(question: str) -> Iterator[AgentEvent]:
        return run_agent(
            question,
            backend=backend,
            registry=registry,
            context_builder=builder,
            max_turns=max_turns,
        )

    return run_question


def _cmd_chat(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    connector = make_connector(config.database)
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
            _chat_one_question(question, run_question, verbose=args.verbose)
    except NotImplementedError as exc:
        print(f"\n[BLOCKED] {exc}", file=sys.stderr)
        print(
            "agent.py / safety.py 为 HUMAN-OWNED（规格 §〇），由人类实现后 CLI 即可运行。",
            file=sys.stderr,
        )
        return 1
    finally:
        connector.close()
    return 0


def _chat_one_question(question: str, run_question: RunQuestion, *, verbose: bool) -> None:
    pending = question
    while True:
        clarify: ClarifyEvent | None = None
        for event in run_question(pending):
            if isinstance(event, ClarifyEvent):
                clarify = event
            _render_event(event, verbose)
        if clarify is None:
            return
        # v0.2.0 reserved branch: fold the user's reply back into the question
        # and continue; mechanism to be finalised with the human agent design.
        try:
            reply = input("你答> ").strip()
        except EOFError:
            return
        if not reply:
            return
        pending = f"{pending}\n(用户补充说明: {reply})"


def _cmd_eval(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if args.backend or args.model or args.base_url:
        config = dataclasses.replace(
            config,
            llm=LLMConfig(
                backend=args.backend or config.llm.backend,
                model=args.model or config.llm.model,
                base_url=args.base_url or config.llm.base_url,
            ),
        )
    try:
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
    except NotImplementedError as exc:
        print(f"\n[BLOCKED] {exc}", file=sys.stderr)
        print(
            "eval 需要 agent.py / safety.py（HUMAN-OWNED）实现后才能运行。",
            file=sys.stderr,
        )
        return 1
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


if __name__ == "__main__":
    raise SystemExit(main())
