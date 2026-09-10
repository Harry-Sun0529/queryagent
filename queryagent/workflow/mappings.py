"""Load the maintainer-declared 口径 → SQL mapping table.

Separate file from ``metrics.yaml`` on purpose. The metric file answers
"what does the business mean"; this file answers "and which query is the
approved way to get it". They have different reviewers and different blast
radii: a wrong sentence in a definition confuses a reader, a wrong statement
here silently produces a wrong number under a correct-looking 口径 (§18).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_TABLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?")
_COLUMN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class QueryMapping:
    """A maintainer-declared way to compute one (metric, variant), in parts.

    The parts are what let a confirmed period reach the SQL: the compiler
    adds a condition on ``time_column``, which it could not do inside a
    whole statement without parsing it. ``measure`` and ``where`` are SQL
    fragments with exactly the trust of a whole ``sql:`` entry — written by
    a maintainer, reviewed as a diff. ``source`` and ``time_column`` must be
    plain identifiers, checked when the file is loaded.
    """

    source: str
    measure: str
    label: str
    time_column: str = ""
    where: tuple[str, ...] = ()


Mappings = dict[tuple[str, str], "str | QueryMapping"]


def load_mappings(path: str | Path) -> Mappings:
    """Parse a mappings YAML file.

    Schema::

        mappings:
          - metric: new_users
            variant: registered      # optional; omit for metrics without variants
            from: users              # structured (slice 1C): a period can be applied
            measure: COUNT(*)
            label: 新增用户数
            time_column: created_at  # optional; without it a period is refused
            where: ["channel <> 'internal_test'"]
          - metric: legacy
            sql: SELECT ...          # a whole statement: runs as written, refuses a period

    Raises:
        ValueError: On any structural problem, naming the offending entry.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("mappings"), list):
        raise ValueError(f"{path}: expected a top-level 'mappings' list")
    table: Mappings = {}
    for index, item in enumerate(raw["mappings"]):
        key, entry = _parse_entry(item, f"mappings[{index}]")
        if key in table:
            raise ValueError(f"{path}: duplicate mapping for {key[0]}/{key[1] or '(no variant)'}")
        table[key] = entry
    return table


def _parse_entry(item: Any, where: str) -> tuple[tuple[str, str], str | QueryMapping]:
    if not isinstance(item, dict):
        raise ValueError(f"{where}: each mapping must be a mapping")
    metric = item.get("metric")
    if not isinstance(metric, str) or not metric.strip():
        raise ValueError(f"{where}: 'metric' is required and must be a non-empty string")
    variant = item.get("variant", "")
    if not isinstance(variant, str):
        raise ValueError(f"{where}: 'variant' must be a string when present")
    key = (metric.strip(), variant.strip())
    structured = {"from", "measure", "label", "time_column", "where"} & set(item)
    if "sql" in item:
        if structured:
            raise ValueError(
                f"{where} ({metric}): give either 'sql' or the structured fields, not both"
            )
        sql = item["sql"]
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError(f"{where} ({metric}): 'sql' must be a non-empty string")
        return key, sql.strip()
    return key, _parse_structured(item, f"{where} ({metric})")


def _parse_structured(item: dict[str, Any], where: str) -> QueryMapping:
    fields: dict[str, str] = {}
    for name in ("from", "measure", "label"):
        value = item.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{where}: '{name}' is required (or give a whole 'sql')")
        fields[name] = " ".join(value.split())
    if not _TABLE.fullmatch(fields["from"]):
        raise ValueError(f"{where}: 'from' must be a table name, got {fields['from']!r}")
    if any(mark in fields["label"] for mark in ('"', "`", "'")):
        raise ValueError(f"{where}: 'label' must not contain quote characters")
    time_column = item.get("time_column", "")
    if not isinstance(time_column, str) or (time_column and not _COLUMN.fullmatch(time_column)):
        raise ValueError(f"{where}: 'time_column' must be a column name, got {time_column!r}")
    raw_where = item.get("where") or []
    if not isinstance(raw_where, list) or not all(
        isinstance(c, str) and c.strip() for c in raw_where
    ):
        raise ValueError(f"{where}: 'where' must be a list of non-empty strings")
    return QueryMapping(
        source=fields["from"],
        measure=fields["measure"],
        label=fields["label"],
        time_column=time_column,
        where=tuple(" ".join(c.split()) for c in raw_where),
    )
