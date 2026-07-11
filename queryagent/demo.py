"""Temporary demo entrypoint for v0.1.0 — replaced by ``cli.py`` in v0.1.1.

This is the only place in v0.1.0 that renders events; it is a plain consumer
of the event stream (spec §二).

Usage:
    python -m queryagent.demo "上个月每天的新增用户数" \\
        [--config examples/demo_ecommerce/config.yaml] [--max-turns 8]
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
from queryagent.schema import render_schema
from queryagent.tools import ToolRegistry, make_default_tools


def main(argv: Sequence[str] | None = None) -> int:
    """Run one question end to end against the configured database."""
    parser = argparse.ArgumentParser(description="QueryAgent v0.1.0 demo")
    parser.add_argument("question", help="natural-language question")
    parser.add_argument("--config", default="examples/demo_ecommerce/config.yaml")
    parser.add_argument("--max-turns", type=int, default=8)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    connector = make_connector(config.database)
    try:
        backend = make_backend(config.llm)
        schema_text = render_schema(connector.get_schema())
        builder = ContextBuilder(schema_text=schema_text, dialect=connector.dialect)
        registry = ToolRegistry(
            make_default_tools(
                connector,
                timeout_s=config.safety.timeout_s,
                max_rows=config.safety.max_rows,
            )
        )
        for event in run_agent(
            args.question,
            backend=backend,
            registry=registry,
            context_builder=builder,
            max_turns=args.max_turns,
        ):
            _print_event(event)
    except NotImplementedError as exc:
        print(f"\n[BLOCKED] {exc}", file=sys.stderr)
        print(
            "agent.py / safety.py 为 HUMAN-OWNED（规格 §〇），由人类实现后此 demo 即可运行。",
            file=sys.stderr,
        )
        return 1
    finally:
        connector.close()
    return 0


def _print_event(event: AgentEvent) -> None:
    if isinstance(event, ThinkEvent):
        print(f"[THINK] {event.text}")
    elif isinstance(event, ToolCallEvent):
        print(f"[ACT] {event.tool_name} {event.arguments}")
    elif isinstance(event, ObservationEvent):
        prefix = "[OBSERVE:ERROR]" if event.is_error else "[OBSERVE]"
        print(f"{prefix}\n{event.content}")
    elif isinstance(event, RetryEvent):
        print(f"[RETRY #{event.attempt}] {event.reason}")
    elif isinstance(event, ClarifyEvent):
        print(f"[CLARIFY] {event.question} (metrics: {', '.join(event.conflicting_metrics)})")
    elif isinstance(event, AnswerEvent):
        print(f"\n[ANSWER]\n{event.text}")
    elif isinstance(event, ErrorEvent):
        print(f"[ERROR] {event.error_type}: {event.message}")


if __name__ == "__main__":
    raise SystemExit(main())
