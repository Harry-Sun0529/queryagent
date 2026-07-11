"""ClickHouse connector (clickhouse-driver, native TCP protocol).

Optional extra: ``pip install queryagent[clickhouse]``. Imported lazily by
``make_connector`` so the base install never needs the driver.

Row caps ride ClickHouse's own ``result_overflow_mode='break'`` (server stops
accumulating blocks past ``max_result_rows``), then re-cap client-side for an
exact ``max_rows``; timeouts use the server-side ``max_execution_time``.
"""

from __future__ import annotations

from typing import Any

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseDriverError

from queryagent.connectors.base import QueryResult
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
    ) -> None:
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

    def execute(self, sql: str, *, timeout_s: int, max_rows: int) -> QueryResult:
        """Run one query with server-side timeout and row-cap settings."""
        settings: dict[str, Any] = {
            "max_execution_time": timeout_s,
            "max_result_rows": max_rows + 1,
            "result_overflow_mode": "break",
        }
        try:
            raw_rows, column_defs = self._client.execute(
                sql, with_column_types=True, settings=settings
            )
        except ClickHouseDriverError as exc:
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
