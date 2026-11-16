"""The local SQLite files are opened by several processes at once."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from queryagent.sqlite_state import OPEN_DEADLINE_S, open_shared

SCHEMA = "CREATE TABLE IF NOT EXISTS t (x INTEGER);"


class Flaky:
    """A ``connect`` whose first ``refusals`` connections cannot switch to WAL."""

    def __init__(self, refusals: int, message: str = "database is locked") -> None:
        self.refusals = refusals
        self.message = message
        self.opened: list[sqlite3.Connection] = []

    def __call__(self, path: Path, **options: object) -> sqlite3.Connection:
        refuse = len(self.opened) < self.refusals
        connection = (
            _Refusing(self.message) if refuse else sqlite3.connect(path, **options)  # type: ignore[arg-type]
        )
        self.opened.append(connection)  # type: ignore[arg-type]
        return connection  # type: ignore[return-value]


class _Refusing:
    def __init__(self, message: str) -> None:
        self._message = message
        self.closed = False

    def execute(self, _sql: str) -> None:
        raise sqlite3.OperationalError(self._message)

    def close(self) -> None:
        self.closed = True


def test_an_open_that_loses_the_race_for_the_file_is_tried_again(tmp_path: Path) -> None:
    """Switching to WAL while another process does the same fails at once, without waiting."""
    connect = Flaky(refusals=3)
    pauses: list[float] = []
    connection = open_shared(tmp_path / "s.db", SCHEMA, connect=connect, sleep=pauses.append)
    connection.execute("INSERT INTO t VALUES (1)")
    assert connection.execute("SELECT x FROM t").fetchone()["x"] == 1
    assert len(connect.opened) == 4
    assert pauses == sorted(pauses) and len(pauses) == 3  # backs off, does not spin
    connection.close()


def test_an_open_still_locked_at_the_deadline_says_so(tmp_path: Path) -> None:
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        open_shared(
            tmp_path / "s.db",
            SCHEMA,
            connect=Flaky(refusals=10_000),
            sleep=sleep,
            clock=lambda: now[0],
        )
    assert now[0] >= OPEN_DEADLINE_S


def test_an_error_that_is_not_a_lock_is_not_retried(tmp_path: Path) -> None:
    connect = Flaky(refusals=5, message="file is not a database")
    with pytest.raises(sqlite3.OperationalError, match="not a database"):
        open_shared(tmp_path / "s.db", SCHEMA, connect=connect, sleep=lambda _s: None)
    assert len(connect.opened) == 1


def test_several_processes_opening_a_new_state_file_at_once_all_succeed(tmp_path: Path) -> None:
    """The real thing, in real processes: an MCP server, a page and a terminal starting together."""
    code = (
        "import sys; from queryagent.workflow.store import SqliteWorkflowStore; "
        "SqliteWorkflowStore(sys.argv[1]).close()"
    )
    for trial in range(6):
        path = tmp_path / f"wf-{trial}.db"
        started = [
            subprocess.Popen([sys.executable, "-c", code, str(path)], stderr=subprocess.PIPE)
            for _ in range(6)
        ]
        failures = [p.communicate()[1].decode()[-200:] for p in started if p.wait() != 0]
        assert failures == []
