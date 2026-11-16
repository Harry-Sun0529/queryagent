"""QueryAgent CLI: ``chat`` (interactive, multi-turn), ``ask`` (one-shot),
``eval`` (scored suites) — all pure consumers of the AgentEvent stream —
plus ``flow``, which is not.

``flow`` drives the trusted workflow layer instead: it prepares a 口径, shows
it, requires an explicit confirmation, and only then executes a
maintainer-declared query. It shares no execution path with ``ask``/``chat``;
that is the point of it (see CONTEXT.md, "Two paths, deliberately separate").

``--verbose`` renders the full THINK/ACT/OBSERVE trace; the default shows
answers only. In chat, a ClarifyEvent renders the agent's question, folds
the user's reply back into the pending question and re-runs; answered turns
are kept as session conversation so follow-ups can refer back.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from queryagent.cli.chat import (
    MAX_REMEMBERED_TURNS,
    _cmd_ask,
    _cmd_chat,
    _cmd_replay,
    _make_run_question,
)
from queryagent.cli.errors import (
    EXIT_EVAL_FAILED,
    EXIT_INTERNAL_DEFECT,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_TEMPORARY_FAILURE,
    EXIT_USER_ERROR,
    _explain,
    _is_temporary,
    _report_error,
)
from queryagent.cli.evaluate import _cmd_eval, _OutageGuard, _WorkerPool
from queryagent.cli.flow import (
    _cmd_confirm,
    _cmd_drafts,
    _cmd_flow,
    _cmd_kb,
    _cmd_mcp,
    _cmd_web,
)
from queryagent.cli.parser import build_parser
from queryagent.cli.prompts import _ask_until_valid

__all__ = [
    "EXIT_EVAL_FAILED",
    "EXIT_INTERNAL_DEFECT",
    "EXIT_INTERRUPTED",
    "EXIT_OK",
    "EXIT_TEMPORARY_FAILURE",
    "EXIT_USER_ERROR",
    "MAX_REMEMBERED_TURNS",
    "_OutageGuard",
    "_WorkerPool",
    "_ask_until_valid",
    "_explain",
    "_is_temporary",
    "_make_run_question",
    "build_parser",
    "main",
]


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``queryagent`` console script."""
    args = build_parser().parse_args(argv)
    handlers = {
        "chat": _cmd_chat,
        "ask": _cmd_ask,
        "flow": _cmd_flow,
        "mcp": _cmd_mcp,
        "web": _cmd_web,
        "drafts": _cmd_drafts,
        "confirm": _cmd_confirm,
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
        return EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001 - top level: explain, never dump a traceback
        return _report_error(exc, verbose=getattr(args, "verbose", False))
