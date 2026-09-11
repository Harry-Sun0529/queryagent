"""Data source connectors behind the ``Connector`` protocol."""

from __future__ import annotations

from queryagent.config import DatabaseConfig
from queryagent.connectors.base import Connector
from queryagent.connectors.mysql import MySQLConnector
from queryagent.connectors.sqlite import SQLiteConnector


def make_connector(config: DatabaseConfig, *, max_rows_scanned: int | None = None) -> Connector:
    """Build the connector matching a validated database config.

    ``max_rows_scanned`` (``budget.max_rows_scanned``) reaches ClickHouse
    only; config loading refuses it for any other database.
    """
    if config.type == "mysql":
        return MySQLConnector(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
        )
    if config.type == "sqlite":
        return SQLiteConnector(path=config.path)
    if config.type == "clickhouse":
        # Lazy import: clickhouse-driver is an optional extra
        # (pip install queryagent[clickhouse]).
        from queryagent.connectors.clickhouse import ClickHouseConnector

        return ClickHouseConnector(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            max_rows_scanned=max_rows_scanned,
        )
    raise ValueError(f"unsupported database type: {config.type}")
