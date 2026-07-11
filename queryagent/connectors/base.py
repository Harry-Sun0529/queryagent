"""Data source abstraction (spec §二).

New data sources implement this protocol and nothing else changes — v0.1.1
validates the seam with SQLite and (schedule permitting) ClickHouse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from queryagent.schema import TableSchema


@dataclass(frozen=True)
class QueryResult:
    """Result of a read query.

    Attributes:
        columns: Column names in select order.
        rows: Row tuples, already capped at the connector's ``max_rows``.
        elapsed_ms: Wall-clock query time in milliseconds.
        truncated: True when the row cap cut off further results.
    """

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    elapsed_ms: int
    truncated: bool


class Connector(Protocol):
    """Contract for data sources.

    ``dialect`` is injected into the system prompt so the model generates SQL
    in the right flavour. Errors are raised as ``QueryError`` carrying the
    dialect's original error text (fed back to the model for self-repair).
    """

    dialect: str

    def get_schema(self) -> list[TableSchema]:
        """Return the schema of every table visible to the connection."""
        ...

    def execute(self, sql: str, *, timeout_s: int, max_rows: int) -> QueryResult:
        """Run one read query with enforced timeout and row cap."""
        ...

    def close(self) -> None:
        """Release all underlying connections; call once, after all queries."""
        ...
