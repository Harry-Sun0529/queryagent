"""Opening the local SQLite files several processes share.

The workflow state, the budget ledger and the document index are each one
SQLite file that more than one process opens: an MCP server beside a
confirmation page beside a terminal is the ordinary way to run this.

Statements wait for each other through SQLite's busy timeout. Opening does
not: switching a file to WAL while another connection is doing the same
returns "database is locked" at once, without waiting, and so can creating
the schema. Found by the acceptance checks, which start two MCP servers on a
fresh state file: about one start in forty lost that race and exited. So the
opening sequence is retried here, in the one place all three files open.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

OPEN_DEADLINE_S = 10.0
_FIRST_PAUSE_S = 0.02
_LONGEST_PAUSE_S = 0.5


def open_shared(
    path: str | Path,
    schema: str,
    *,
    timeout_s: float = 10.0,
    named_rows: bool = True,
    connect: Callable[..., sqlite3.Connection] = sqlite3.connect,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> sqlite3.Connection:
    """A WAL connection to ``path`` with ``schema`` in place, shared safely.

    Args:
        path: The file; its directory is created if missing.
        schema: ``CREATE … IF NOT EXISTS`` statements, safe to run again.
        timeout_s: How long a statement waits on another process's lock.
        named_rows: Rows as ``sqlite3.Row`` (by column name) rather than tuples.
        connect, sleep, clock: Seams for the tests.

    Raises:
        sqlite3.OperationalError: Still locked after ``OPEN_DEADLINE_S``, or
            any error that is not a lock.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    deadline = clock() + OPEN_DEADLINE_S
    pause = _FIRST_PAUSE_S
    while True:
        connection = connect(target, isolation_level=None, timeout=timeout_s)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(schema)
        except sqlite3.OperationalError as exc:
            connection.close()
            if not is_lock_error(exc) or clock() >= deadline:
                raise
            sleep(pause)
            pause = min(pause * 2, _LONGEST_PAUSE_S)
            continue
        if named_rows:
            connection.row_factory = sqlite3.Row
        return connection


def is_lock_error(exc: sqlite3.OperationalError) -> bool:
    """Whether another connection held the file, rather than the file being wrong."""
    text = str(exc).lower()
    return "locked" in text or "busy" in text
