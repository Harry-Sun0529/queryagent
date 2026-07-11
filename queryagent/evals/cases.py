"""Eval case model and YAML loading (spec §三 v0.2.0).

The YAML schema allows a ``tags`` field from day one — reserved for slicing
reports by capability dimension later (spec §三 本版预留).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

KINDS = frozenset({"simple", "metric", "multistep", "clarify", "no_clarify", "public"})


@dataclass(frozen=True)
class EvalCase:
    """One eval case.

    Attributes:
        id: Unique case identifier.
        question: The natural-language question posed to the agent.
        kind: One of ``KINDS``; drives which checks apply.
        expected_sql: Reference SQL executed to produce the expected result
            set (required unless kind == "clarify").
        expected_metrics: For "clarify" cases: metric names that must appear
            in the ClarifyEvent. For "metric" cases: strings that must appear
            in the final answer (metric names or display names).
        tags: Free-form labels, reserved for report slicing.
        db_id: Public-benchmark cases only — which database to run against.
    """

    id: str
    question: str
    kind: str
    expected_sql: str = ""
    expected_metrics: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    db_id: str = ""


def load_cases(path: str | Path) -> list[EvalCase]:
    """Load and validate an eval cases YAML file.

    Raises:
        ValueError: On structural problems, naming the offending case.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        raise ValueError(f"{path}: expected a top-level 'cases' list")
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for index, item in enumerate(raw["cases"]):
        case = _parse_case(item, index)
        if case.id in seen:
            raise ValueError(f"duplicate case id: {case.id}")
        seen.add(case.id)
        cases.append(case)
    return cases


def _parse_case(item: Any, index: int) -> EvalCase:
    where = f"cases[{index}]"
    if not isinstance(item, dict):
        raise ValueError(f"{where}: each case must be a mapping")
    case_id = _req_str(item, "id", where)
    where = f"{where} ({case_id})"
    kind = _req_str(item, "kind", where)
    if kind not in KINDS:
        raise ValueError(f"{where}: kind must be one of {sorted(KINDS)}, got '{kind}'")
    expected_sql = str(item.get("expected_sql") or "").strip()
    if kind != "clarify" and not expected_sql:
        raise ValueError(f"{where}: expected_sql is required for kind '{kind}'")
    expected_metrics = _str_tuple(item, "expected_metrics", where)
    if kind == "clarify" and not expected_metrics:
        raise ValueError(f"{where}: clarify cases must declare expected_metrics")
    return EvalCase(
        id=case_id,
        question=_req_str(item, "question", where),
        kind=kind,
        expected_sql=expected_sql,
        expected_metrics=expected_metrics,
        tags=_str_tuple(item, "tags", where),
        db_id=str(item.get("db_id") or "").strip(),
    )


def _req_str(item: dict[str, Any], key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: '{key}' is required and must be a non-empty string")
    return value.strip()


def _str_tuple(item: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = item.get(key) or []
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        raise ValueError(f"{where}: '{key}' must be a list of strings when present")
    return tuple(entry.strip() for entry in value if entry.strip())
