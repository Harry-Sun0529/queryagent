"""Unit tests for the SQLite connector — real queries, no mocks."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.errors import ConnectorError, QueryError


@pytest.fixture
def connector(tmp_path: Path) -> Iterator[SQLiteConnector]:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id INTEGER NOT NULL, name TEXT, created_at TEXT)")
    conn.executemany(
        "INSERT INTO users VALUES (?, ?, ?)",
        [(i, f"user{i}", "2026-07-01 00:00:00") for i in range(1, 11)],
    )
    conn.commit()
    conn.close()
    instance = SQLiteConnector(path=str(db_path))
    yield instance
    instance.close()


def test_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConnectorError, match="not found"):
        SQLiteConnector(path=str(tmp_path / "nope.db"))


def test_get_schema(connector: SQLiteConnector) -> None:
    tables = connector.get_schema()
    assert [t.name for t in tables] == ["users"]
    columns = {c.name: c for c in tables[0].columns}
    assert columns["id"].nullable is False
    assert columns["name"].nullable is True


def test_execute_returns_rows_and_columns(connector: SQLiteConnector) -> None:
    result = connector.execute(
        "SELECT id, name FROM users ORDER BY id LIMIT 2", timeout_s=5, max_rows=100
    )
    assert result.columns == ("id", "name")
    assert result.rows == ((1, "user1"), (2, "user2"))
    assert result.truncated is False


def test_row_cap_sets_truncated(connector: SQLiteConnector) -> None:
    result = connector.execute("SELECT id FROM users", timeout_s=5, max_rows=5)
    assert len(result.rows) == 5
    assert result.truncated is True


def test_error_wrapped_as_query_error(connector: SQLiteConnector) -> None:
    with pytest.raises(QueryError) as exc_info:
        connector.execute("SELECT * FROM missing_table", timeout_s=5, max_rows=10)
    assert exc_info.value.dialect == "sqlite"
    assert "missing_table" in exc_info.value.original_error


def test_timeout_aborts_runaway_query(connector: SQLiteConnector) -> None:
    infinite = (
        "WITH RECURSIVE c(x) AS (VALUES(1) UNION ALL SELECT x + 1 FROM c) "
        "SELECT count(*) FROM c"
    )
    with pytest.raises(QueryError):
        connector.execute(infinite, timeout_s=1, max_rows=10)
