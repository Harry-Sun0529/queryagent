"""Shared JSON-to-dataclass rebuilding for persisted records.

Traces and eval checkpoints are both append-only JSONL of frozen dataclasses,
and both need the same two properties: a field absent from the payload falls
back to its default (so a file written by another version still loads), and
JSON's lists become tuples again where the field declares one (so a
round-trip compares equal). Keeping one implementation means a future field
type is handled once rather than fixed twice.
"""

from __future__ import annotations

import dataclasses
from typing import Any, TypeVar

T = TypeVar("T")


def rebuild_dataclass(cls: type[T], payload: dict[str, Any]) -> T:
    """Construct ``cls`` from ``payload``, ignoring fields it does not know.

    Args:
        cls: A dataclass type.
        payload: Decoded JSON for one record.

    Returns:
        An instance of ``cls``; missing fields take their declared defaults.

    Raises:
        TypeError: If a field without a default is missing from the payload.
    """
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(cls):  # type: ignore[arg-type]
        if field.name not in payload:
            continue
        value = payload[field.name]
        if isinstance(value, list) and "tuple" in str(field.type):
            value = tuple(value)
        kwargs[field.name] = value
    return cls(**kwargs)
