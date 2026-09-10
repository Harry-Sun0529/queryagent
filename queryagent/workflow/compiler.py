"""Confirmed definition → SQL, from maintainer-declared mappings only.

Two properties, both about refusal. A definition no maintainer mapped is
refused rather than guessed (D09, T14). And a confirmed period is either
applied or refused — never dropped: a whole-statement ``sql:`` mapping cannot
take a date condition without the compiler parsing SQL, so it refuses a
period instead of running an all-time query under a monthly 口径 (§11.2).

Values are bound, not interpolated (ADR-009, superseding ADR-008's typed
compilation). The statement text holds only maintainer SQL fragments, which
carry the same trust as the whole statements they replace, and ``?``
placeholders; the dates of a confirmed period travel beside it as
parameters, each decoded from a strictly-shaped rule first. Nothing the user
typed and nothing a document said is ever part of the text.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from queryagent.workflow.errors import MappingNotFound, WorkflowStateError
from queryagent.workflow.mappings import QueryMapping
from queryagent.workflow.models import PERIOD_RULE_KEY, VARIANT_RULE_KEY, BusinessDefinition
from queryagent.workflow.periods import Period


@dataclass(frozen=True)
class CompiledQuery:
    """A statement and the values bound into it.

    ``sql`` uses ``?`` placeholders, filled in order from ``params`` by the
    connector's driver. The pair is what a run records, so the audit trail
    shows the statement exactly as it was sent and the values separately.
    """

    sql: str
    params: tuple[str, ...] = ()


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

    def compile(self, definition: BusinessDefinition) -> CompiledQuery:
        """Return the statement and values for this confirmed definition.

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
            return CompiledQuery(entry)
        return _compose(entry, period, self._dialect, where)

    def freshness_probe(self, definition: BusinessDefinition) -> CompiledQuery | None:
        """The statement that dates the data behind this definition, if one exists.

        ``MAX(time_column)`` over the mapping's whole table, without its
        ``where`` fragments: the question is how far the data reaches, not
        how far this metric's filtered rows do — a paid-orders filter can end
        early for business reasons that say nothing about loading. None when
        there is no structured mapping with a time column to read.
        """
        rule = definition.rule(VARIANT_RULE_KEY)
        entry = self._templates.get((definition.metric, rule.value if rule else ""))
        if not isinstance(entry, QueryMapping) or not entry.time_column:
            return None
        return CompiledQuery(f"SELECT MAX({entry.time_column}) FROM {entry.source}")


def _period_of(definition: BusinessDefinition) -> Period | None:
    rule = definition.rule(PERIOD_RULE_KEY)
    if rule is None:
        return None
    try:
        return Period.decode(rule.value)
    except ValueError as exc:
        raise WorkflowStateError(f"统计区间不是规范格式：{rule.value!r}") from exc


def _compose(
    entry: QueryMapping, period: Period | None, dialect: str, where: str
) -> CompiledQuery:
    # Maintainer fragments are parenthesised so an OR inside one cannot
    # escape the period condition beside it.
    conditions = [f"({fragment})" for fragment in entry.where]
    params: tuple[str, ...] = ()
    if period is not None:
        if not entry.time_column:
            raise MappingNotFound(
                f"{where} 的映射没有声明 time_column，无法施加统计区间 {period.render()}"
            )
        # Bound as bare ISO dates, not 'YYYY-MM-DD 00:00:00'. A column storing
        # dates as text ('2026-08-01') sorts *below* '2026-08-01 00:00:00' in
        # SQLite, so a timestamp-shaped lower bound silently dropped the first
        # day of every period. A bare date bounds date-only and timestamp text
        # alike, and MySQL and ClickHouse both read it as midnight. Strings
        # rather than date objects: sqlite3's default date adapter is
        # deprecated, and the drivers would render the same text anyway.
        conditions += [f"{entry.time_column} >= ?", f"{entry.time_column} < ?"]
        params = (period.start.isoformat(), period.end_exclusive.isoformat())
    clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT {entry.measure} AS {_quote(entry.label, dialect)} FROM {entry.source}{clause}"
    return CompiledQuery(sql, params)


def _quote(label: str, dialect: str) -> str:
    """Quote a result-column alias for the dialect. Labels are validated
    quote-free at load time, so this cannot be broken out of."""
    return f"`{label}`" if dialect == "mysql" else f'"{label}"'
