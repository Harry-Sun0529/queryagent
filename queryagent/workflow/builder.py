"""Turn a question into a draft 口径 (slice 1A: maintainer metrics only).

This is deliberately the shallow version. Slice 1B replaces it with a builder
over authorised document evidence, where candidates carry citations and
``missing`` is derived from what the documents actually fail to say. The
interface — question in, structured definition with candidates and gaps out —
is what stays.

What is already true here and must remain true: a metric that has competing
readings produces a draft that is *incomplete*, not a draft that quietly
picked the first reading.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import date

from queryagent.metrics.base import Metric, MetricStore
from queryagent.workflow.errors import MappingNotFound
from queryagent.workflow.models import (
    PERIOD_RULE_KEY,
    REQUIRABLE_RULE_KEYS,
    VARIANT_RULE_KEY,
    BusinessDefinition,
    Candidate,
    Rule,
    RuleSource,
)
from queryagent.workflow.periods import PeriodError, find_period


class MetricDraftBuilder:
    """Build a draft definition from the maintainer's declared metrics."""

    def __init__(self, metrics: MetricStore, *, today: Callable[[], date] = date.today) -> None:
        """
        Args:
            metrics: The maintainer's declared metrics.
            today: Which day relative time words are resolved against. The CLI
                passes the configured business time zone's date; tests pass a
                fixed one.
        """
        self._metrics = metrics
        self._today = today

    def build(self, question: str) -> BusinessDefinition:
        """Return the definition to show the user.

        Raises:
            MappingNotFound: No declared metric applies. Reported as a fact
                rather than answered from a guess (T25).
        """
        matches = self._metrics.match(question, top_k=1)
        if not matches:
            raise MappingNotFound(
                f"no declared business metric matches this question: {question!r}"
            )
        return _with_period(_definition_for(matches[0]), question, self._today())


def _with_period(definition: BusinessDefinition, question: str, today: date) -> BusinessDefinition:
    """Read the question's time words into a period rule, in absolute dates.

    One recognisable period becomes a 本次约定 rule naming the words it came
    from — the user asked for it, and they confirm the dates it resolves to.
    Two different periods, or an impossible date, leave the period missing
    whether or not the metric requires one: the question asked for a period,
    so running without it would answer a different question.
    """
    try:
        found = find_period(question, today)
    except PeriodError:
        if PERIOD_RULE_KEY in definition.missing:
            return definition
        return dataclasses.replace(definition, missing=(*definition.missing, PERIOD_RULE_KEY))
    if found is None:
        return definition
    rule = Rule(
        PERIOD_RULE_KEY,
        found.period.encode(),
        RuleSource.USER,
        note=f"由问题中的「{found.phrase}」换算",
    )
    return definition.with_rules((rule,))


def _definition_for(metric: Metric) -> BusinessDefinition:
    rules = [
        Rule(
            key="metric",
            value=metric.display_name or metric.name,
            source=RuleSource.MAINTAINER,
        ),
        Rule(key="definition", value=metric.definition, source=RuleSource.MAINTAINER),
    ]
    if metric.tables:
        rules.append(
            Rule(key="tables", value=", ".join(metric.tables), source=RuleSource.MAINTAINER)
        )
    candidates = tuple(
        Candidate(key=v.key, label=v.label, summary=v.definition) for v in metric.variants
    )
    # A declared disagreement is a hole in the definition until the user
    # closes it — not a default the system picks on their behalf (D05, D02).
    unknown = [key for key in metric.required_rules if key not in REQUIRABLE_RULE_KEYS]
    if unknown:
        raise ValueError(
            f"metrics.yaml: {metric.name}.required_rules has unknown keys {unknown}; "
            f"allowed: {', '.join(REQUIRABLE_RULE_KEYS)}"
        )
    # Required rules are gaps until something states them: a document, or the
    # user this time. Never a default the system fills in (§4.5.5, D07).
    missing = ((VARIANT_RULE_KEY,) if candidates else ()) + metric.required_rules
    return BusinessDefinition(
        metric=metric.name,
        display_name=metric.display_name or metric.name,
        rules=tuple(rules),
        missing=missing,
        candidates=candidates,
    )
