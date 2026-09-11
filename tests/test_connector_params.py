"""Slice 1C-2: values reach the database as parameters, in each driver's own form (T36).

The workflow writes ``?`` placeholders. SQLite binds them; PyMySQL and
clickhouse-driver substitute client-side with ``query % escaped``, which
reads every other ``%`` in the statement as a directive. The live halves of
F1/F2 are in the MySQL and ClickHouse integration files; this file proves
the translation offline, including by running it through ``%`` formatting
exactly as the drivers do.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from queryagent.connectors.params import to_pyformat
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.errors import QueryError

FRAGMENT = "SELECT COUNT(*) FROM users WHERE channel LIKE '%ga%' AND created_at >= ?"


def test_placeholders_become_positional_directives_and_literal_percents_are_doubled() -> None:
    assert to_pyformat(FRAGMENT, 1, named=False) == (
        "SELECT COUNT(*) FROM users WHERE channel LIKE '%%ga%%' AND created_at >= %s"
    )


def test_named_style_numbers_the_placeholders_in_order() -> None:
    sql = "SELECT 1 FROM t WHERE a >= ? AND a < ?"
    assert to_pyformat(sql, 2, named=True) == "SELECT 1 FROM t WHERE a >= %(p0)s AND a < %(p1)s"


def test_after_driver_formatting_the_maintainers_percents_mean_what_they_said() -> None:
    """F2: what the driver sends is the statement as written, with the value in place."""
    formatted = to_pyformat(FRAGMENT, 1, named=False) % ("'2026-08-01'",)
    assert formatted == FRAGMENT.replace("?", "'2026-08-01'")
    named = to_pyformat(FRAGMENT, 1, named=True) % {"p0": "'2026-08-01'"}
    assert named == formatted


def test_a_question_mark_inside_a_string_literal_is_not_a_placeholder() -> None:
    sql = "SELECT 1 FROM t WHERE note = 'why?' AND a >= ?"
    assert to_pyformat(sql, 1, named=False) == "SELECT 1 FROM t WHERE note = 'why?' AND a >= %s"


def test_a_directive_the_maintainer_wrote_is_escaped_not_obeyed() -> None:
    """A literal %s in a fragment must not swallow a parameter meant for a ?."""
    sql = "SELECT 1 FROM t WHERE code = '%s' AND a >= ?"
    assert (to_pyformat(sql, 1, named=False) % ("'x'",)) == sql.replace("?", "'x'")


def test_a_placeholder_count_that_disagrees_with_the_values_is_refused() -> None:
    with pytest.raises(ValueError, match="2 placeholders but 1"):
        to_pyformat("SELECT 1 FROM t WHERE a >= ? AND a < ?", 1, named=False)


def _db(tmp_path: Path) -> str:
    path = tmp_path / "t.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE users (created_at TEXT, channel TEXT)")
    connection.executemany(
        "INSERT INTO users VALUES (?, ?)",
        [("2026-07-31", "organic"), ("2026-08-01", "organic"), ("2026-08-02", "ads")],
    )
    connection.commit()
    connection.close()
    return str(path)


def test_sqlite_binds_the_values(tmp_path: Path) -> None:
    connector = SQLiteConnector(path=_db(tmp_path))
    try:
        result = connector.execute(FRAGMENT, timeout_s=5, max_rows=5, params=("2026-08-01",))
    finally:
        connector.close()
    assert result.rows == ((1,),)


def test_without_values_a_connector_runs_the_statement_as_before(tmp_path: Path) -> None:
    """F3: the agent's execute_sql path passes no params and must not change."""
    connector = SQLiteConnector(path=_db(tmp_path))
    try:
        result = connector.execute("SELECT COUNT(*) FROM users", timeout_s=5, max_rows=5)
    finally:
        connector.close()
    assert result.rows == ((3,),)


def test_sqlite_reports_a_missing_value_as_a_query_error(tmp_path: Path) -> None:
    connector = SQLiteConnector(path=_db(tmp_path))
    try:
        with pytest.raises(QueryError, match="bindings"):
            connector.execute(FRAGMENT, timeout_s=5, max_rows=5)
    finally:
        connector.close()
