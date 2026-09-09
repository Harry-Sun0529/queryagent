"""Load the maintainer-declared 口径 → SQL mapping table.

Separate file from ``metrics.yaml`` on purpose. The metric file answers
"what does the business mean"; this file answers "and which query is the
approved way to get it". They have different reviewers and different blast
radii: a wrong sentence in a definition confuses a reader, a wrong statement
here silently produces a wrong number under a correct-looking 口径 (§18).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

Mappings = dict[tuple[str, str], str]


def load_mappings(path: str | Path) -> Mappings:
    """Parse a mappings YAML file.

    Schema::

        mappings:
          - metric: new_users
            variant: registered      # optional; omit for metrics without variants
            sql: SELECT ...

    Raises:
        ValueError: On any structural problem, naming the offending entry.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("mappings"), list):
        raise ValueError(f"{path}: expected a top-level 'mappings' list")
    table: Mappings = {}
    for index, item in enumerate(raw["mappings"]):
        key, sql = _parse_entry(item, f"mappings[{index}]")
        if key in table:
            raise ValueError(f"{path}: duplicate mapping for {key[0]}/{key[1] or '(no variant)'}")
        table[key] = sql
    return table


def _parse_entry(item: Any, where: str) -> tuple[tuple[str, str], str]:
    if not isinstance(item, dict):
        raise ValueError(f"{where}: each mapping must be a mapping")
    metric = item.get("metric")
    if not isinstance(metric, str) or not metric.strip():
        raise ValueError(f"{where}: 'metric' is required and must be a non-empty string")
    variant = item.get("variant", "")
    if not isinstance(variant, str):
        raise ValueError(f"{where}: 'variant' must be a string when present")
    sql = item.get("sql")
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError(f"{where} ({metric}): 'sql' is required and must be a non-empty string")
    return (metric.strip(), variant.strip()), sql.strip()
