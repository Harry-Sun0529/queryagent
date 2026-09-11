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
from queryagent.workflow.grouping import (
    DAY,
    DIMENSION_PREFIX,
    FILTER_NONE,
    MONTH,
    NONE,
    TIME_GRAINS,
    WEEK,
    Dimension,
    is_filter,
    is_grouping,
    split_filter,
)
from queryagent.workflow.mappings import QueryMapping, mapping_fingerprint
from queryagent.workflow.models import (
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    VARIANT_RULE_KEY,
    BusinessDefinition,
)
from queryagent.workflow.periods import Period

# One expression per time grain per dialect, each returning the group's first
# day as a date. Closed and code-reviewed: nothing here comes from a user or a
# mapping file except the column name, which is validated as an identifier.
# Weeks start on Monday. SQLite's 'weekday 1' moves *forward* to a Monday,
# so it is applied after stepping back six days.
_GRAIN_SQL = {
    DAY: {"sqlite": "date({col})", "mysql": "DATE({col})", "clickhouse": "toDate({col})"},
    WEEK: {
        "sqlite": "date({col}, '-6 days', 'weekday 1')",
        "mysql": "DATE(DATE_SUB({col}, INTERVAL WEEKDAY({col}) DAY))",
        "clickhouse": "toMonday({col})",
    },
    MONTH: {
        "sqlite": "date({col}, 'start of month')",
        "mysql": "DATE(DATE_SUB({col}, INTERVAL DAYOFMONTH({col}) - 1 DAY))",
        "clickhouse": "toStartOfMonth({col})",
    },
}
_GRAIN_ALIASES = {DAY: "日期", WEEK: "周起始日", MONTH: "月份"}


@dataclass(frozen=True)
class CompiledQuery:
    """A statement and the values bound into it.

    ``sql`` uses ``?`` placeholders, filled in order from ``params`` by the
    connector's driver. The pair is what a run records, so the audit trail
    shows the statement exactly as it was sent and the values separately.
    """

    sql: str
    params: tuple[str, ...] = ()


@dataclass(frozen=True)
class FreshnessTarget:
    """One table and time column whose newest record dates a definition's data.

    ``lag_days`` is the maintainer's declared cadence for it (T+N), or None.
    """

    source: str
    time_column: str
    lag_days: int | None = None

    @property
    def probe(self) -> CompiledQuery:
        """``MAX(time_column)`` over identifiers validated when the mappings loaded."""
        return CompiledQuery(f"SELECT MAX({self.time_column}) FROM {self.source}")


class TemplateCompiler:
    """Compiles a confirmed definition through the maintainer's mapping table."""

    def __init__(
        self,
        templates: Mapping[tuple[str, str], str | QueryMapping],
        *,
        dialect: str = "sqlite",
        dimensions: tuple[Dimension, ...] = (),
    ) -> None:
        self._templates = dict(templates)
        self._dialect = dialect
        self._dimensions = dimensions

    def compile(self, definition: BusinessDefinition) -> CompiledQuery:
        """Return the statement and values for this confirmed definition.

        Raises:
            MappingNotFound: No mapping covers it, or the mapping cannot apply
                the confirmed period.
            WorkflowStateError: The period rule is not in canonical form —
                it can only have been produced by something other than the
                period parser.
        """
        entry, where = self._lookup(definition)
        if entry is None:
            raise MappingNotFound(
                f"no maintainer-defined query mapping for {where}; "
                "a mapping must be declared before this 口径 can be executed"
            )
        period = _period_of(definition)
        grouping = _grouping_of(definition)
        value_filter = _filter_of(definition)
        if isinstance(entry, str):
            if period is not None:
                raise MappingNotFound(
                    f"{where} 的映射是整条 SQL，无法施加已确认的统计区间 {period.render()}；"
                    "请维护者改为结构化映射（from / measure / time_column）。"
                    "不会忽略区间去跑全量。"
                )
            if grouping not in ("", NONE):
                raise MappingNotFound(
                    f"{where} 的映射是整条 SQL，无法按已确认的方式分组；"
                    "请维护者改为结构化映射。不会忽略分组去给一个总数。"
                )
            if value_filter:
                raise MappingNotFound(
                    f"{where} 的映射是整条 SQL，无法按已确认的取值过滤；"
                    "请维护者改为结构化映射。不会忽略过滤去给全部数据的数字。"
                )
            return CompiledQuery(entry)
        return _compose(
            entry, period, self._dialect, where, grouping, self._dimensions, value_filter
        )

    def freshness_probe(self, definition: BusinessDefinition) -> CompiledQuery | None:
        """The statement that dates the data behind this definition, if one exists.

        ``MAX(time_column)`` over the mapping's whole table, without its
        ``where`` fragments: the question is how far the data reaches, not
        how far this metric's filtered rows do — a paid-orders filter can end
        early for business reasons that say nothing about loading. None when
        there is no structured mapping with a time column to read.
        """
        entry, _ = self._lookup(definition)
        if not isinstance(entry, QueryMapping) or not entry.time_column:
            return None
        return FreshnessTarget(entry.source, entry.time_column).probe

    def freshness_targets(self, definition: BusinessDefinition) -> tuple[FreshnessTarget, ...]:
        """The tables that date this definition's data, before or after a reading is chosen.

        With a reading chosen, its mapping's table. Before, every reading's —
        deduplicated, since two readings over one column ask the data one
        question (T41). Whole-statement mappings and mappings without a time
        column date nothing and are skipped.
        """
        entry, _ = self._lookup(definition)
        entries = (
            [entry]
            if entry is not None
            else [item for key, item in self._templates.items() if key[0] == definition.metric]
        )
        found: dict[tuple[str, str], FreshnessTarget] = {}
        for item in entries:
            if isinstance(item, QueryMapping) and item.time_column:
                found.setdefault(
                    (item.source, item.time_column),
                    FreshnessTarget(item.source, item.time_column, item.lag_days),
                )
        return tuple(found.values())

    def fingerprint(self, definition: BusinessDefinition) -> str:
        """The digest of the mapping this definition would run, or '' if none (T42)."""
        entry, _ = self._lookup(definition)
        return mapping_fingerprint(entry) if entry is not None else ""

    def _lookup(self, definition: BusinessDefinition) -> tuple[str | QueryMapping | None, str]:
        """The mapping for this definition's metric and reading, and its name."""
        rule = definition.rule(VARIANT_RULE_KEY)
        variant = rule.value if rule else ""
        where = f"{definition.metric}/{variant}" if variant else definition.metric
        return self._templates.get((definition.metric, variant)), where


def _period_of(definition: BusinessDefinition) -> Period | None:
    rule = definition.rule(PERIOD_RULE_KEY)
    if rule is None:
        return None
    try:
        return Period.decode(rule.value)
    except ValueError as exc:
        raise WorkflowStateError(f"统计区间不是规范格式：{rule.value!r}") from exc


def _grouping_of(definition: BusinessDefinition) -> str:
    rule = definition.rule(GROUP_RULE_KEY)
    if rule is None:
        return ""
    if not is_grouping(rule.value):
        raise WorkflowStateError(f"分组方式不是规范值：{rule.value!r}")
    return rule.value


def _filter_of(definition: BusinessDefinition) -> str:
    """The confirmed ``dim:key=value`` filter, or '' for none."""
    rule = definition.rule(FILTER_RULE_KEY)
    if rule is None:
        return ""
    if not is_filter(rule.value):
        raise WorkflowStateError(f"过滤条件不是规范值：{rule.value!r}")
    return "" if rule.value == FILTER_NONE else rule.value


def _declared_column(
    entry: QueryMapping, key: str, where: str, dimensions: tuple[Dimension, ...], action: str
) -> tuple[Dimension, str]:
    """The declared dimension and its column in this mapping's table, or refuse.

    Never joins to find one: a dimension the maintainer did not declare for
    this table is not one this query may split or filter by.
    """
    dimension = next((d for d in dimensions if d.key == key), None)
    column = dimension.column_for(entry.source) if dimension else None
    if dimension is None or column is None:
        name = dimension.label if dimension else key
        raise MappingNotFound(
            f"{where} 取自表 {entry.source}，维护者没有为它声明维度「{name}」，无法按它{action}"
        )
    return dimension, column


def _filter_condition(
    entry: QueryMapping, value_filter: str, where: str, dimensions: tuple[Dimension, ...]
) -> tuple[str, str]:
    """``column = ?`` and the value bound to it (T43)."""
    key, stored = split_filter(value_filter) or ("", "")
    dimension, column = _declared_column(entry, key, where, dimensions, "过滤")
    if dimension.value_for(stored) != stored:
        # The parser only produces declared values; a stored rule that is not
        # one did not come from it, and must not become a filter matching nothing.
        raise WorkflowStateError(f"「{dimension.label}」没有声明取值 {stored!r}")
    return f"{column} = ?", stored


def _group_key(
    entry: QueryMapping,
    grouping: str,
    dialect: str,
    where: str,
    dimensions: tuple[Dimension, ...],
) -> tuple[str, str] | None:
    """The GROUP BY expression and its column alias, or None for one total."""
    if grouping in ("", NONE):
        return None
    if grouping in TIME_GRAINS:
        if not entry.time_column:
            raise MappingNotFound(f"{where} 的映射没有声明 time_column，无法按时间分组")
        template = _GRAIN_SQL[grouping].get(dialect)
        if template is None:
            raise MappingNotFound(f"方言 {dialect} 尚不支持按时间分组")
        return template.format(col=entry.time_column), _GRAIN_ALIASES[grouping]
    key = grouping[len(DIMENSION_PREFIX) :]
    dimension, column = _declared_column(entry, key, where, dimensions, "分组")
    return column, dimension.label


def _compose(
    entry: QueryMapping,
    period: Period | None,
    dialect: str,
    where: str,
    grouping: str = "",
    dimensions: tuple[Dimension, ...] = (),
    value_filter: str = "",
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
    if value_filter:
        condition, stored = _filter_condition(entry, value_filter, where, dimensions)
        conditions.append(condition)
        params = (*params, stored)
    clause =f" WHERE {' AND '.join(conditions)}" if conditions else ""
    measure = f"{entry.measure} AS {_quote(entry.label, dialect)}"
    key = _group_key(entry, grouping, dialect, where, dimensions)
    if key is None:
        return CompiledQuery(f"SELECT {measure} FROM {entry.source}{clause}", params)
    expression, alias = key
    # The expression is repeated rather than referenced by alias or position:
    # that is the one form all three dialects accept under strict GROUP BY.
    sql = (
        f"SELECT {expression} AS {_quote(alias, dialect)}, {measure} FROM {entry.source}{clause}"
        f" GROUP BY {expression} ORDER BY {expression}"
    )
    return CompiledQuery(sql, params)


def _quote(label: str, dialect: str) -> str:
    """Quote a result-column alias for the dialect. Labels are validated
    quote-free at load time, so this cannot be broken out of."""
    return f"`{label}`" if dialect == "mysql" else f'"{label}"'
