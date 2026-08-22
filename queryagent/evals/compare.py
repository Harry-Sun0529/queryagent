"""Result-set comparison: order-insensitive multiset equality with float tolerance.

Why compare execution results instead of SQL text (spec §三 v0.2.0; ADR-003
to be written by the human): equivalent SQL is syntactically diverse — column
aliases, CTE vs subquery, join order — so executed row sets are the only
robust equivalence oracle at this project's scale.

Float handling: values are rounded to ``_FLOAT_DECIMALS`` decimal places
before comparison. Rounding is an absolute-tolerance proxy that keeps rows
hashable, which multiset counting needs; a true pairwise ``isclose`` match
would be O(n²) and was rejected for simplicity (row caps keep n small, but
hashability also keeps the code obvious).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

_FLOAT_DECIMALS = 4


def normalize_value(value: Any) -> Any:
    """Normalise one cell so equivalent values compare equal across drivers.

    MySQL returns Decimal/datetime objects where SQLite returns float/str;
    booleans arrive as ints from some drivers. Everything unknown falls back
    to ``str``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, (float, Decimal)):
        return round(float(value), _FLOAT_DECIMALS)
    if isinstance(value, datetime):
        # An offset-aware value is converted to UTC first: formatting without
        # the offset made 12:00Z and 12:00+08:00 — eight hours apart — compare
        # equal. Naive values are left as written; inventing a zone for them
        # would be guessing.
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def normalize_rows(rows: Sequence[Sequence[Any]]) -> Counter[tuple[Any, ...]]:
    """Normalise rows into a multiset (duplicates matter, order does not)."""
    return Counter(tuple(normalize_value(value) for value in row) for row in rows)


def rows_match(expected: Sequence[Sequence[Any]], actual: Sequence[Sequence[Any]]) -> bool:
    """True when both row sets are equal as multisets after normalisation.

    Row width differences make tuples unequal, so a query returning extra
    columns fails the comparison — matching the expected_sql column contract
    is part of correctness.
    """
    return normalize_rows(expected) == normalize_rows(actual)
