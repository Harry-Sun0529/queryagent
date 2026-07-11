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
import sys
from collections.abc import Sequence

from queryagent.agent import run_agent
from queryagent.config import load_config
from queryagent.connectors import make_connector
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
)
from queryagent.llm import make_backend
from queryagent.llm.base import LLMBackend
from queryagent.schema import render_schema
from queryagent.tools import ToolRegistry, make_default_tools


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``queryagent`` console script."""
    parser = argparse.ArgumentParser(prog="queryagent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    chat = subparsers.add_parser("chat", help="interactive Q&A against the configured database")
    chat.add_argument("--config", default="config.yaml", help="path to config.yaml")
    chat.add_argument("--verbose", action="store_true", help="show the full agent trace")
    chat.add_argument("--max-turns", type=int, default=8)
    args = parser.parse_args(argv)
    if args.command == "chat":
        return _cmd_chat(args)
    return 2


def _cmd_chat(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    connector = make_connector(config.database)
    try:
        backend = make_backend(config.llm)
        builder = ContextBuilder(
            schema_text=render_schema(connector.get_schema()),
            dialect=connector.dialect,
        )
        registry = ToolRegistry(
            make_default_tools(
                connector,
                timeout_s=config.safety.timeout_s,
                max_rows=config.safety.max_rows,
            )
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
            _run_question(
                question,
                backend=backend,
                registry=registry,
                builder=builder,
                max_turns=args.max_turns,
                verbose=args.verbose,
            )
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


def _run_question(
    question: str,
    *,
    backend: LLMBackend,
    registry: ToolRegistry,
    builder: ContextBuilder,
    max_turns: int,
    verbose: bool,
) -> None:
    pending = question
    while True:
        clarify: ClarifyEvent | None = None
        for event in run_agent(
            pending,
            backend=backend,
            registry=registry,
            context_builder=builder,
            max_turns=max_turns,
        ):
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
