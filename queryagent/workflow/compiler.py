"""Confirmed definition → SQL, from maintainer-declared mappings only.

Two properties, both about refusal. A definition no maintainer mapped is
refused rather than guessed (D09, T14). And a confirmed period is either
applied or refused — never dropped: a whole-statement ``sql:`` mapping cannot
take a date condition without the compiler parsing SQL, so it refuses a
period instead of running an all-time query under a monthly 口径 (§11.2).

Typed, not parameterised (slice 1C, C01). Exactly two kinds of value reach
the statement: maintainer SQL fragments, which carry the same trust as the
whole statements they replace, and dates that exist only as ``datetime.date``
objects decoded from a strictly-shaped rule. Nothing the user typed and
nothing a document said is ever interpolated. Parameter binding would need a
Connector protocol change across three dialects and is a later step.
"""

from __future__ import annotations

from collections.abc import Mapping

from queryagent.workflow.errors import MappingNotFound, WorkflowStateError
from queryagent.workflow.mappings import QueryMapping
from queryagent.workflow.models import PERIOD_RULE_KEY, VARIANT_RULE_KEY, BusinessDefinition
from queryagent.workflow.periods import Period


class TemplateCompiler:
    """Compiles a confirmed definition through the maintainer's mapping table."""

    def __init__(
        self,
        templates: Mapping[tuple[str, str], str | QueryMapping],
        *,
        dialect: str = "sqlite",
    ) -> None:
        self._templates = dict(templates)
        self._dialect = dialect

    def compile(self, definition: BusinessDefinition) -> str:
        """Return the SQL for this confirmed definition.

        Raises:
            MappingNotFound: No mapping covers it, or the mapping cannot apply
                the confirmed period.
            WorkflowStateError: The period rule is not in canonical form —
                it can only have been produced by something other than the
                period parser.
        """
        rule = definition.rule(VARIANT_RULE_KEY)
        variant = rule.value if rule else ""
        where = f"{definition.metric}/{variant}" if variant else definition.metric
        entry = self._templates.get((definition.metric, variant))
        if entry is None:
            raise MappingNotFound(
                f"no maintainer-defined query mapping for {where}; "
                "a mapping must be declared before this 口径 can be executed"
            )
        period = _period_of(definition)
        if isinstance(entry, str):
            if period is not None:
                raise MappingNotFound(
                    f"{where} 的映射是整条 SQL，无法施加已确认的统计区间 {period.render()}；"
                    "请维护者改为结构化映射（from / measure / time_column）。"
                    "不会忽略区间去跑全量。"
                )
            return entry
        return _compose(entry, period, self._dialect, where)


def _period_of(definition: BusinessDefinition) -> Period | None:
    rule = definition.rule(PERIOD_RULE_KEY)
    if rule is None:
        return None
    try:
        return Period.decode(rule.value)
    except ValueError as exc:
        raise WorkflowStateError(f"统计区间不是规范格式：{rule.value!r}") from exc


def _compose(entry: QueryMapping, period: Period | None, dialect: str, where: str) -> str:
    # Maintainer fragments are parenthesised so an OR inside one cannot
    # escape the period condition beside it.
    conditions = [f"({fragment})" for fragment in entry.where]
    if period is not None:
        if not entry.time_column:
            raise MappingNotFound(
                f"{where} 的映射没有声明 time_column，无法施加统计区间 {period.render()}"
            )
        # Bare dates, not 'YYYY-MM-DD 00:00:00'. A column storing dates as text
        # ('2026-08-01') sorts *below* '2026-08-01 00:00:00' in SQLite, so a
        # timestamp-shaped lower bound silently dropped the first day of every
        # period. A bare date bounds date-only and timestamp text alike, and
        # MySQL and ClickHouse both read it as midnight.
        start = period.start.isoformat()
        end = period.end_exclusive.isoformat()
        conditions += [f"{entry.time_column} >= '{start}'", f"{entry.time_column} < '{end}'"]
    clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return f"SELECT {entry.measure} AS {_quote(entry.label, dialect)} FROM {entry.source}{clause}"


def _quote(label: str, dialect: str) -> str:
    """Quote a result-column alias for the dialect. Labels are validated
    quote-free at load time, so this cannot be broken out of."""
    return f"`{label}`" if dialect == "mysql" else f'"{label}"'
