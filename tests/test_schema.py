"""Unit tests for schema rendering."""

from __future__ import annotations

from queryagent.schema import ColumnSchema, TableSchema, render_schema


def test_render_schema_includes_tables_columns_and_comments() -> None:
    tables = [
        TableSchema(
            name="users",
            comment="registered users",
            columns=(
                ColumnSchema(name="id", type="bigint", nullable=False, comment="user id"),
                ColumnSchema(name="first_order_at", type="datetime", nullable=True),
            ),
        ),
        TableSchema(name="channels", columns=(ColumnSchema(name="code", type="varchar(64)"),)),
    ]
    text = render_schema(tables)
    assert "TABLE users" in text
    assert "registered users" in text
    assert "id bigint NOT NULL" in text
    assert "first_order_at datetime NULL" in text
    assert "TABLE channels" in text


def test_render_schema_empty() -> None:
    assert render_schema([]) == ""


def big_schema(n_tables: int, n_cols: int = 25) -> list[TableSchema]:
    return [
        TableSchema(
            name=f"tbl_{i}",
            columns=tuple(
                ColumnSchema(name=f"col_{j}", type="varchar(255)", comment="业务字段说明")
                for j in range(n_cols)
            ),
        )
        for i in range(n_tables)
    ]


def test_large_schema_is_bounded() -> None:
    # A 300-table database is ordinary; unbounded it rendered ~75k tokens,
    # which blew the context budget and forced query results out of history.
    text = render_schema(big_schema(300), max_chars=20_000)
    assert len(text) <= 20_000


def test_every_table_name_survives_bounding() -> None:
    # Losing detail is acceptable; silently hiding a table is not — the agent
    # would never know to ask about it.
    text = render_schema(big_schema(300), max_chars=20_000)
    for i in (0, 150, 299):
        assert f"tbl_{i}" in text


def test_bounding_is_announced() -> None:
    text = render_schema(big_schema(300), max_chars=20_000)
    assert "abbreviated" in text.lower() or "get_schema" in text


def test_small_schema_keeps_full_detail() -> None:
    tables = [
        TableSchema(
            name="users",
            comment="registered users",
            columns=(ColumnSchema(name="id", type="bigint", nullable=False, comment="user id"),),
        )
    ]
    text = render_schema(tables, max_chars=20_000)
    assert "id bigint NOT NULL" in text
    assert "user id" in text
    assert "abbreviated" not in text.lower()


def test_moderate_schema_degrades_before_dropping_columns() -> None:
    # 50 tables x 20 columns: too big for full detail, small enough that
    # column names should still be visible after comments are dropped.
    text = render_schema(big_schema(50, n_cols=20), max_chars=20_000)
    assert "col_19" in text
    assert len(text) <= 20_000
