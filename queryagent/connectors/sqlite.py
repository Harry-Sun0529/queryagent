"""SQLite connector — stdlib only, the zero-Docker demo path (spec §三 v0.1.1).

Timeout note: SQLite has no per-query timeout, so this connector uses a
progress handler as a deadline guard — SQLite invokes it every N virtual
machine instructions, and a non-zero return aborts the running statement.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from queryagent.connectors.base import QueryResult
from queryagent.errors import ConnectorError, QueryError
from queryagent.schema import ColumnSchema, TableSchema

_PROGRESS_INTERVAL = 10_000  # VM instructions between deadline checks


class SQLiteConnector:
    """Connector implementation over the standard library ``sqlite3``."""

    dialect = "sqlite"

    def __init__(self, *, path: str) -> None:
        """Open the database file.

        Raises:
            ConnectorError: If the file does not exist — connecting to a
                missing path would silently create an empty database and
                yield a confusing "no tables" experience instead.
        """
        if path != ":memory:" and not Path(path).exists():
            raise ConnectorError(f"SQLite database not found: {path}")
        # check_same_thread=False because a parallel eval builds one
        # connector per worker thread and closes them from the main thread as
        # its ExitStack unwinds. The invariant that makes this safe is that a
        # connection is never *used* by two threads: each worker owns its own,
        # and closing happens only after every worker has finished.
        self._conn = sqlite3.connect(path, check_same_thread=False)

    def get_schema(self) -> list[TableSchema]:
        """Read table/column metadata via sqlite_master and PRAGMA table_info."""
        try:
            names = [
                str(row[0])
                for row in self._conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            tables = []
            for name in names:
                quoted = name.replace('"', '""')
                columns = tuple(
                    ColumnSchema(
                        name=str(row[1]),
                        type=str(row[2]) or "ANY",
                        nullable=row[3] == 0,
                    )
                    for row in self._conn.execute(f'PRAGMA table_info("{quoted}")')
                )
                tables.append(TableSchema(name=name, columns=columns))
        except sqlite3.Error as exc:
            raise QueryError(str(exc), dialect=self.dialect) from exc
        return tables

    def execute(self, sql: str, *, timeout_s: int, max_rows: int) -> QueryResult:
        """Run one query with a deadline guard and a row cap."""
        start = time.monotonic()
        deadline = start + timeout_s

        def guard() -> int:
            return 1 if time.monotonic() > deadline else 0

        self._conn.set_progress_handler(guard, _PROGRESS_INTERVAL)
        try:
            cursor = self._conn.execute(sql)
            raw_rows = cursor.fetchmany(max_rows + 1)
            columns = tuple(str(desc[0]) for desc in cursor.description or ())
        except sqlite3.Error as exc:
            raise QueryError(str(exc), dialect=self.dialect) from exc
        finally:
            self._conn.set_progress_handler(None, 0)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        truncated = len(raw_rows) > max_rows
        rows = tuple(tuple(row) for row in raw_rows[:max_rows])
        return QueryResult(columns=columns, rows=rows, elapsed_ms=elapsed_ms, truncated=truncated)

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()
