"""Every command and flag of ``queryagent``, and who the local user is.

Part of the 1.0 contract (ADR-014): ``tests/contract`` snapshots what this builds.
"""

from __future__ import annotations

import argparse
import os


def _local_subject() -> str:
    """Who the local CLI user is: the same default ``flow --subject`` takes."""
    return os.environ.get("USER", "local")

def build_parser() -> argparse.ArgumentParser:
    """Every command and flag. Part of the 1.0 contract, snapshotted in tests/contract."""
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
    flow.add_argument("--subject", default=_local_subject(), help="acting user id")
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
        "--group-by",
        dest="group_by",
        help="split the result: day, week, month, a declared dimension (e.g. channel), "
        "or none for one total; recorded as 本次约定",
    )
    flow.add_argument(
        "--filter",
        dest="value_filter",
        help="count only one declared value of a dimension (e.g. 渠道=广告, channel=ads), "
        "or none for every value; recorded as 本次约定",
    )
    flow.add_argument(
        "--no-history",
        dest="no_history",
        action="store_true",
        help="do not offer the choices you confirmed last time for this metric. With --yes "
        "they are never offered: nobody would read them before the run",
    )
    flow.add_argument(
        "--yes",
        action="store_true",
        help="confirm the 口径 without prompting. The confirmation record is still "
        "created server-side and bound to this exact version — this flag automates "
        "the human, it does not bypass the gate.",
    )

    mcp = subparsers.add_parser(
        "mcp",
        help="serve the confirmation-gated flow to an agent over MCP (stdio). The agent can "
        "prepare, amend and execute; only a person confirms, in the terminal or the page",
    )
    mcp.add_argument("--config", default="config.yaml", help="path to config.yaml")
    mcp.add_argument(
        "--subject",
        default=_local_subject(),
        help="the person the agent acts for; no tool argument can change it",
    )
    mcp.add_argument("--workspace", default="default", help="business workspace id")
    mcp.add_argument(
        "--no-history",
        dest="no_history",
        action="store_true",
        help="do not offer the choices this person confirmed last time",
    )

    web = subparsers.add_parser(
        "web",
        help="the local confirmation page (127.0.0.1 only): review and confirm what an "
        "agent prepared",
    )
    web.add_argument("--config", default="config.yaml", help="path to config.yaml")
    web.add_argument("--subject", default=_local_subject(), help="the person confirming")
    web.add_argument("--workspace", default="default", help="business workspace id")
    web.add_argument("--port", type=int, default=8765, help="port on 127.0.0.1 (default 8765)")

    drafts = subparsers.add_parser("drafts", help="list the 口径 waiting for your confirmation")
    drafts.add_argument("--config", default="config.yaml", help="path to config.yaml")
    drafts.add_argument("--subject", default=_local_subject(), help="acting user id")
    drafts.add_argument("--workspace", default="default", help="business workspace id")

    confirm = subparsers.add_parser(
        "confirm",
        help="review one draft in the terminal and confirm it; the agent that prepared it "
        "then executes it, once",
    )
    confirm.add_argument(
        "draft_id", help="the draft id, or its first characters as the sheet shows them"
    )
    confirm.add_argument("--config", default="config.yaml", help="path to config.yaml")
    confirm.add_argument("--subject", default=_local_subject(), help="acting user id")
    confirm.add_argument("--workspace", default="default", help="business workspace id")

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

    return parser
