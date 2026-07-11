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
