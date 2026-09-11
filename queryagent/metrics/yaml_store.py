"""YAML-backed metric store (spec §三 v0.1.1).

Matching policy (all deliberate, tuned against the self-built eval set):
- exact phrase hits on display_name/aliases score 10x a token overlap — a
  verbatim alias in the question is near-certain intent;
- a minimum score of 2 filters single-shared-bigram noise: "有多少用户" must
  NOT match 新增用户 just because both contain 用户 (eval showed such weak
  matches leak metric filters into unrelated questions);
- definitions are excluded from matching (long text drags in noise);
- ties keep YAML file order (stable sort), so authors control precedence.

YAML schema (required fields frozen at v0.1.1; optional fields may be added):

    metrics:
      - name: new_users            # required, unique
        display_name: 新增用户
        aliases: [新用户, new users]
        definition: >              # required — the prompt-injection body
          按 users.created_at 日期计数；……
        caution: 运营口径按 first_order_at……   # optional; v0.2.0 clarify fuel
        tables: [users]            # optional
        sql_hint: "COUNT(*) ..."   # optional
        variants:                  # optional; selectable competing readings
          - key: registered
            label: 注册口径
            definition: 按 users.created_at 归属日期
        required_rules: [time_window]  # optional; rules the 口径 must state
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from queryagent.metrics.base import Metric, MetricVariant
from queryagent.text import tokens

_PHRASE_HIT_SCORE = 10.0  # one verbatim alias hit outweighs any token overlap
_MIN_SCORE = 2.0  # a single shared bigram/word is noise, not a match

METRIC_KEYS = (
    "name",
    "display_name",
    "aliases",
    "definition",
    "caution",
    "tables",
    "sql_hint",
    "variants",
    "required_rules",
)
"""Every key a metric may carry (the 1.0 file contract, ADR-014). A misspelt
one is refused: 'required_rule' read as absent would stop asking a question."""
VARIANT_KEYS = ("key", "label", "definition")


class YamlMetricStore:
    """MetricStore over one YAML file: alias hits + keyword-overlap scoring."""

    def __init__(self, path: str | Path) -> None:
        """Load and validate the metrics file.

        Raises:
            ValueError: On structural problems (missing required fields,
                duplicate names, wrong types), with the offending entry named.
        """
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("metrics"), list):
            raise ValueError(f"{path}: expected a top-level 'metrics' list")
        self._metrics: dict[str, Metric] = {}
        for index, item in enumerate(raw["metrics"]):
            metric = _parse_metric(item, index)
            if metric.name in self._metrics:
                raise ValueError(f"duplicate metric name: {metric.name}")
            self._metrics[metric.name] = metric

    def get(self, name: str) -> Metric | None:
        """Exact lookup by unique metric name."""
        return self._metrics.get(name)

    def all(self) -> tuple[Metric, ...]:
        """Every declared metric, in file order."""
        return tuple(self._metrics.values())

    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        """Score every metric against the question; return top_k with score > 0.

        Scoring = exact phrase hits (display_name/aliases appearing verbatim,
        case-insensitive, in the question) weighted heavily, plus token
        overlap between the question and the metric's name/display_name/aliases.
        """
        question_lower = question.lower()
        question_tokens = tokens(question)
        scored: list[tuple[float, Metric]] = []
        for metric in self._metrics.values():
            score = 0.0
            for phrase in (metric.display_name, *metric.aliases):
                if phrase and phrase.lower() in question_lower:
                    score += _PHRASE_HIT_SCORE
            metric_tokens = tokens(" ".join((metric.name, metric.display_name, *metric.aliases)))
            score += len(question_tokens & metric_tokens)
            if score >= _MIN_SCORE:
                scored.append((score, metric))
        scored.sort(key=lambda pair: pair[0], reverse=True)  # stable: ties keep file order
        return [metric for _, metric in scored[:top_k]]


def _parse_metric(item: Any, index: int) -> Metric:
    where = f"metrics[{index}]"
    if not isinstance(item, dict):
        raise ValueError(f"{where}: each metric must be a mapping")
    _refuse_unknown(item, METRIC_KEYS, where)
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{where}: 'name' is required and must be a non-empty string")
    definition = item.get("definition")
    if not isinstance(definition, str) or not definition.strip():
        raise ValueError(f"{where} ({name}): 'definition' is required")
    return Metric(
        name=name.strip(),
        definition=definition.strip(),
        display_name=_opt_str(item, "display_name", where),
        aliases=_str_tuple(item, "aliases", where),
        caution=_opt_str(item, "caution", where),
        tables=_str_tuple(item, "tables", where),
        sql_hint=_opt_str(item, "sql_hint", where),
        variants=_variants(item, where),
        required_rules=_str_tuple(item, "required_rules", where),
    )


def _variants(item: dict[str, Any], where: str) -> tuple[MetricVariant, ...]:
    """Parse optional competing readings; every field is required per entry.

    A variant with no label or no definition cannot be shown to a user as a
    choice, so a partial one is a config error rather than something to
    render half of.
    """
    value = item.get("variants") or []
    if not isinstance(value, list):
        raise ValueError(f"{where}: 'variants' must be a list when present")
    parsed: list[MetricVariant] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        at = f"{where}.variants[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{at}: each variant must be a mapping")
        _refuse_unknown(entry, VARIANT_KEYS, at)
        fields = {}
        for key in ("key", "label", "definition"):
            text = entry.get(key)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{at}: '{key}' is required and must be a non-empty string")
            fields[key] = text.strip()
        if fields["key"] in seen:
            raise ValueError(f"{at}: duplicate variant key '{fields['key']}'")
        seen.add(fields["key"])
        parsed.append(MetricVariant(**fields))
    return tuple(parsed)


def _refuse_unknown(item: dict[str, Any], allowed: tuple[str, ...], where: str) -> None:
    unknown = sorted(str(key) for key in item if key not in allowed)
    if unknown:
        raise ValueError(f"{where}: unknown keys {unknown}; allowed: {', '.join(allowed)}")


def _opt_str(item: dict[str, Any], key: str, where: str) -> str:
    value = item.get(key, "")
    if not isinstance(value, str):
        raise ValueError(f"{where}: '{key}' must be a string when present")
    return value.strip()


def _str_tuple(item: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = item.get(key) or []
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        raise ValueError(f"{where}: '{key}' must be a list of strings when present")
    return tuple(entry.strip() for entry in value if entry.strip())
