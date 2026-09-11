"""ClickHouse connector (clickhouse-driver, native TCP protocol).

Optional extra: ``pip install queryagent[clickhouse]``. Imported lazily by
``make_connector`` so the base install never needs the driver.

Row caps ride ClickHouse's own ``result_overflow_mode='break'`` (server stops
accumulating blocks past ``max_result_rows``), then re-cap client-side for an
exact ``max_rows``; timeouts use the server-side ``max_execution_time``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseDriverError

from queryagent.connectors.base import QueryResult
from queryagent.connectors.params import to_pyformat
from queryagent.errors import QueryError
from queryagent.schema import ColumnSchema, TableSchema

_TABLES_SQL = (
    "SELECT name, comment FROM system.tables "
    "WHERE database = currentDatabase() ORDER BY name"
)
_COLUMNS_SQL = (
    "SELECT table, name, type, comment FROM system.columns "
    "WHERE database = currentDatabase() ORDER BY table, position"
)
_TOO_MANY_ROWS = 158  # ClickHouse error code when max_rows_to_read is exceeded


class ClickHouseConnector:
    """Connector implementation for ClickHouse 21.x+."""

    dialect = "clickhouse"

    def __init__(
        self,
        *,
        host: str,
        port: int = 9000,
        user: str = "default",
        password: str = "",
        database: str = "default",
        connect_timeout_s: int = 10,
        max_rows_scanned: int | None = None,
    ) -> None:
        # budget.max_rows_scanned (slice 1E): the one scan limit an engine we
        # support enforces itself, rather than a timeout standing in for it.
        self._max_rows_scanned = max_rows_scanned
        self._client = Client(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=connect_timeout_s,
        )

    def get_schema(self) -> list[TableSchema]:
        """Read table/column metadata from the system tables."""
        try:
            table_rows = self._client.execute(_TABLES_SQL)
            column_rows = self._client.execute(_COLUMNS_SQL)
        except ClickHouseDriverError as exc:
            raise QueryError(str(exc), dialect=self.dialect) from exc
        columns_by_table: dict[str, list[ColumnSchema]] = {}
        for table_name, column_name, column_type, comment in column_rows:
            type_text = str(column_type)
            columns_by_table.setdefault(str(table_name), []).append(
                ColumnSchema(
                    name=str(column_name),
                    type=type_text,
                    nullable=type_text.startswith("Nullable("),
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

    def execute(
        self, sql: str, *, timeout_s: int, max_rows: int, params: Sequence[object] = ()
    ) -> QueryResult:
        """Run one query with server-side timeout and row-cap settings.

        clickhouse-driver escapes values client-side and substitutes them
        with ``%`` from a dict, so ``?`` becomes ``%(p0)s``, ``%(p1)s``… and
        the statement's other ``%`` signs are doubled.
        """
        settings: dict[str, Any] = {
            "max_execution_time": timeout_s,
            "max_result_rows": max_rows + 1,
            "result_overflow_mode": "break",
        }
        if self._max_rows_scanned is not None:
            settings["max_rows_to_read"] = self._max_rows_scanned
            settings["read_overflow_mode"] = "throw"
        query = to_pyformat(sql, len(params), named=True) if params else sql
        values = {f"p{index}": value for index, value in enumerate(params)} if params else None
        try:
            raw_rows, column_defs = self._client.execute(
                query, values, with_column_types=True, settings=settings
            )
        except ClickHouseDriverError as exc:
            if getattr(exc, "code", None) == _TOO_MANY_ROWS:
                # Named as the limit it is: a scan budget refusing the read,
                # not a slow query or a broken one (G7). The server's stack
                # trace is noise to the person reading this.
                detail = str(exc).split("Stack trace")[0].strip()
                raise QueryError(
                    f"超过扫描上限：这条语句要读取的行数超过维护者设定的 "
                    f"{self._max_rows_scanned} 行（budget.max_rows_scanned）。{detail}",
                    dialect=self.dialect,
                ) from exc
            raise QueryError(str(exc), dialect=self.dialect) from exc
        elapsed = self._client.last_query.elapsed if self._client.last_query else 0.0
        truncated = len(raw_rows) > max_rows
        rows = tuple(tuple(row) for row in raw_rows[:max_rows])
        columns = tuple(str(name) for name, _ in column_defs)
        return QueryResult(
            columns=columns,
            rows=rows,
            elapsed_ms=int((elapsed or 0.0) * 1000),
            truncated=truncated,
        )

    def close(self) -> None:
        """Disconnect the client."""
        self._client.disconnect()
