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


def render_schema(tables: Sequence[TableSchema]) -> str:
    """Render table schemas as compact plain text for prompt injection.

    Args:
        tables: Schemas as returned by ``Connector.get_schema``.

    Returns:
        A human/model-readable block, one ``TABLE`` section per table.
    """
    blocks: list[str] = []
    for table in tables:
        header = f"TABLE {table.name}"
        if table.comment:
            header += f"  -- {table.comment}"
        lines = [header]
        for column in table.columns:
            null_marker = "NULL" if column.nullable else "NOT NULL"
            line = f"  {column.name} {column.type} {null_marker}"
            if column.comment:
                line += f"  -- {column.comment}"
            lines.append(line)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
