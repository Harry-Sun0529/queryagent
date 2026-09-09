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

from queryagent.metrics.base import Metric, MetricStore
from queryagent.workflow.errors import MappingNotFound
from queryagent.workflow.models import (
    BusinessDefinition,
    Candidate,
    Rule,
    RuleSource,
)

VARIANT_RULE_KEY = "variant"


class MetricDraftBuilder:
    """Build a draft definition from the maintainer's declared metrics."""

    def __init__(self, metrics: MetricStore) -> None:
        self._metrics = metrics

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
        return _definition_for(matches[0])


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
    missing = (VARIANT_RULE_KEY,) if candidates else ()
    return BusinessDefinition(
        metric=metric.name,
        display_name=metric.display_name or metric.name,
        rules=tuple(rules),
        missing=missing,
        candidates=candidates,
    )
