"""Database schema types and prompt rendering."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnSchema:
    """One column: name, dialect-native type text, nullability, comment."""

    name: str
    type: str
    nullable: bool = True
    comment: str = ""


@dataclass(frozen=True)
class TableSchema:
    """One table with its columns and optional table comment."""

    name: str
    columns: tuple[ColumnSchema, ...]
    comment: str = ""


MAX_SCHEMA_CHARS = 20_000


def render_schema(tables: Sequence[TableSchema], *, max_chars: int = MAX_SCHEMA_CHARS) -> str:
    """Render table schemas as compact plain text for prompt injection.

    Real databases have hundreds of tables; rendered in full they can exceed
    the whole context budget, and because trimming only drops whole messages
    the agent would lose its query results to make room. So detail degrades
    in steps until the text fits — comments first, then types, then columns.

    **Table names are never dropped.** Losing a column's type costs the agent
    a follow-up query; losing a table name means it never learns the table
    exists.

    Args:
        tables: Schemas as returned by ``Connector.get_schema``.
        max_chars: Upper bound on the rendered text.

    Returns:
        The most detailed rendering that fits, with a note when it is not the
        full one.
    """
    if not tables:
        return ""
    for level, note in _LEVELS:
        body = "\n\n".join(_render_table(table, level) for table in tables)
        text = body if note is None else f"{body}\n\n{note}"
        if len(text) <= max_chars:
            return text
    names = ", ".join(table.name for table in tables)
    return f"Tables ({len(tables)}): {names}\n\n{_NAMES_ONLY_NOTE}"


_FULL, _NO_COMMENTS, _NO_TYPES, _NAMES = 0, 1, 2, 3

_ABBREVIATED = (
    "(schema abbreviated to fit the context: column comments omitted. "
    "Query the table directly if you need to see example values.)"
)
_NO_TYPES_NOTE = (
    "(schema abbreviated to fit the context: column types and comments omitted.)"
)
_NAMES_ONLY_NOTE = (
    "(schema abbreviated to fit the context: only table names are listed. "
    "Ask about a specific table before querying it.)"
)

_LEVELS: tuple[tuple[int, str | None], ...] = (
    (_FULL, None),
    (_NO_COMMENTS, _ABBREVIATED),
    (_NO_TYPES, _NO_TYPES_NOTE),
)


def _render_table(table: TableSchema, level: int) -> str:
    if level >= _NO_TYPES:
        columns = ", ".join(column.name for column in table.columns)
        return f"TABLE {table.name}: {columns}"
    header = f"TABLE {table.name}"
    if table.comment and level < _NO_COMMENTS:
        header += f"  -- {table.comment}"
    lines = [header]
    for column in table.columns:
        null_marker = "NULL" if column.nullable else "NOT NULL"
        line = f"  {column.name} {column.type} {null_marker}"
        if column.comment and level < _NO_COMMENTS:
            line += f"  -- {column.comment}"
        lines.append(line)
    return "\n".join(lines)
