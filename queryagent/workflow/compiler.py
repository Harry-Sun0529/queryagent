"""Confirmed definition → SQL, via maintainer-declared mappings only.

Slice 1A keeps this a lookup table on purpose. The property worth having
early is not expressiveness but refusal: a definition with no maintainer
mapping produces :class:`MappingNotFound`, never a model-invented query
against tables nobody granted (D09, T14). Slice 1C replaces the table with a
real QueryPlan compiler behind the same call.
"""

from __future__ import annotations

from collections.abc import Mapping

from queryagent.workflow.builder import VARIANT_RULE_KEY
from queryagent.workflow.errors import MappingNotFound
from queryagent.workflow.models import BusinessDefinition


class TemplateCompiler:
    """Maps ``(metric, variant)`` to one maintainer-reviewed SQL statement."""

    def __init__(self, templates: Mapping[tuple[str, str], str]) -> None:
        self._templates = dict(templates)

    def compile(self, definition: BusinessDefinition) -> str:
        """Return the SQL for this confirmed definition.

        Raises:
            MappingNotFound: When no maintainer mapping covers it.
        """
        rule = definition.rule(VARIANT_RULE_KEY)
        variant = rule.value if rule else ""
        sql = self._templates.get((definition.metric, variant))
        if sql is None:
            where = f"{definition.metric}/{variant}" if variant else definition.metric
            raise MappingNotFound(
                f"no maintainer-defined query mapping for {where}; "
                "a mapping must be declared before this 口径 can be executed"
            )
        return sql
