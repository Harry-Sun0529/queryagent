"""MySQL connector: PyMySQL plus a small blocking connection pool.

Read-only defence in depth: the README instructs users to connect with a
SELECT-only account; independently of the SQL safety layer, this connector
enforces per-query timeout and row caps (spec §三 v0.1.0).
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pymysql
import pymysql.cursors

from queryagent.connectors.base import QueryResult
from queryagent.errors import QueryError
from queryagent.schema import ColumnSchema, TableSchema

_TABLES_SQL = (
    "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
    "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME"
)
_COLUMNS_SQL = (
    "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT "
    "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
    "ORDER BY TABLE_NAME, ORDINAL_POSITION"
)


class MySQLConnector:
    """Connector implementation for MySQL 5.7+ / 8.x."""

    dialect = "mysql"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        pool_size: int = 2,
        connect_timeout_s: int = 10,
    ) -> None:
        self._params: dict[str, Any] = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "connect_timeout": connect_timeout_s,
            "charset": "utf8mb4",
            "autocommit": True,
        }
        self._pool: queue.LifoQueue[pymysql.connections.Connection] = queue.LifoQueue()
        self._pool_size = pool_size
        self._created = 0
        self._lock = threading.Lock()

    def get_schema(self) -> list[TableSchema]:
        """Read table/column metadata from information_schema."""
        try:
            with self._connection() as conn, conn.cursor() as cursor:
                cursor.execute(_TABLES_SQL)
                table_rows = cursor.fetchall()
                cursor.execute(_COLUMNS_SQL)
                column_rows = cursor.fetchall()
        except pymysql.MySQLError as exc:
            raise QueryError(str(exc), dialect=self.dialect) from exc
        columns_by_table: dict[str, list[ColumnSchema]] = {}
        for table_name, column_name, column_type, is_nullable, comment in column_rows:
            columns_by_table.setdefault(str(table_name), []).append(
                ColumnSchema(
                    name=str(column_name),
                    type=str(column_type),
                    nullable=is_nullable == "YES",
                    comment=str(comment or ""),
                )
            )
        return [
            TableSchema(
                name=str(table_name),
                columns=tuple(columns_by_table.get(str(table_name), [])),
                comment=str(table_comment or ""),
            )
            for table_name, table_comment in table_rows
        ]

    def execute(self, sql: str, *, timeout_s: int, max_rows: int) -> QueryResult:
        """Run one query; enforce timeout server-side and cap returned rows."""
        start = time.monotonic()
        try:
            with self._connection() as conn, conn.cursor() as cursor:
                _apply_timeout(cursor, timeout_s)
                cursor.execute(sql)
                raw_rows = cursor.fetchmany(max_rows + 1)
                columns = tuple(str(desc[0]) for desc in cursor.description or ())
        except pymysql.MySQLError as exc:
            raise QueryError(str(exc), dialect=self.dialect) from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
        truncated = len(raw_rows) > max_rows
        rows = tuple(tuple(row) for row in raw_rows[:max_rows])
        return QueryResult(columns=columns, rows=rows, elapsed_ms=elapsed_ms, truncated=truncated)

    def close(self) -> None:
        """Close all pooled connections; call after all queries finish."""
        while True:
            try:
                conn = self._pool.get_nowait()
            except queue.Empty:
                break
            try:
                conn.close()
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass

    @contextmanager
    def _connection(self) -> Iterator[pymysql.connections.Connection]:
        """Borrow a pooled connection; dead ones are replaced transparently.

        PyMySQL deprecated ping(reconnect=True), so liveness is checked with
        ping(False) and a failed connection is swapped for a fresh one (the
        pool's created-count is unchanged: one out, one in).
        """
        conn = self._acquire()
        try:
            conn.ping(False)
        except pymysql.MySQLError:
            try:
                conn.close()
            except Exception:  # noqa: BLE001 - already broken, best effort
                pass
            conn = pymysql.connect(**self._params)
        try:
            yield conn
        finally:
            self._pool.put(conn)

    def _acquire(self) -> pymysql.connections.Connection:
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            pass
        with self._lock:
            if self._created < self._pool_size:
                self._created += 1
                try:
                    return pymysql.connect(**self._params)
                except BaseException:
                    self._created -= 1
                    raise
        return self._pool.get()


def _apply_timeout(cursor: pymysql.cursors.Cursor, timeout_s: int) -> None:
    """Best-effort server-side SELECT timeout (MySQL 5.7.8+)."""
    try:
        cursor.execute("SET SESSION MAX_EXECUTION_TIME = %s", (timeout_s * 1000,))
    except pymysql.MySQLError:
        pass  # older servers: connect/read timeouts remain the only guard
