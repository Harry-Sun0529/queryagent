"""Slice 1C: a confirmed period is applied in SQL, or refused — never dropped.

Parsing is test_periods.py; this file proves only what the compiler does
with a confirmed definition. Semantics are checked by executing the compiled
SQL on a real SQLite table built around the month boundaries, because a
string assertion on SQL text cannot tell an off-by-one-day window from a
correct one.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from queryagent.workflow.compiler import CompiledQuery, TemplateCompiler
from queryagent.workflow.errors import MappingNotFound, WorkflowStateError
from queryagent.workflow.mappings import QueryMapping, load_mappings
from queryagent.workflow.models import (
    PERIOD_RULE_KEY,
    BusinessDefinition,
    Rule,
    RuleSource,
)

AUGUST = "2026-08-01..2026-08-31"

REGISTERED = QueryMapping(
    source="users",
    measure="COUNT(*)",
    label="新增用户数",
    time_column="created_at",
    where=("channel <> 'internal_test'",),
)


def _definition(*rules: Rule, variant: str = "registered") -> BusinessDefinition:
    return BusinessDefinition(
        metric="new_users",
        display_name="新增用户",
        rules=(Rule("variant", variant, RuleSource.USER), *rules),
    )


def _august() -> Rule:
    return Rule(PERIOD_RULE_KEY, AUGUST, RuleSource.USER)


def _count(tmp_path: Path, query: CompiledQuery) -> int:
    db = tmp_path / "shop.db"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE users (created_at TEXT, channel TEXT, status TEXT)")
    connection.executemany(
        "INSERT INTO users VALUES (?, ?, ?)",
        [
            ("2026-07-31 23:59:59", "organic", "paid"),  # the day before: out
            ("2026-08-01 00:00:00", "organic", "paid"),  # first instant: in
            ("2026-08-31 23:59:59", "organic", "refunded"),  # last instant: in
            ("2026-09-01 00:00:00", "organic", "paid"),  # next midnight: out
            ("2026-08-15 12:00:00", "internal_test", "paid"),  # filtered by the mapping
        ],
    )
    connection.commit()
    try:
        return int(connection.execute(query.sql, query.params).fetchone()[0])
    finally:
        connection.close()


# ------------------------------------------------------------- P5 applied


def test_a_confirmed_period_includes_both_whole_end_days(tmp_path: Path) -> None:
    """P5: the first instant of the 1st and the last second of the 31st are in."""
    query = TemplateCompiler({("new_users", "registered"): REGISTERED}).compile(
        _definition(_august())
    )
    assert _count(tmp_path, query) == 2


def test_the_period_travels_as_parameters_not_as_text() -> None:
    """F1: the statement holds placeholders; the dates are bound beside it."""
    query = TemplateCompiler({("new_users", "registered"): REGISTERED}).compile(
        _definition(_august())
    )
    assert "2026-" not in query.sql
    assert "created_at >= ? AND created_at < ?" in query.sql
    assert query.params == ("2026-08-01", "2026-09-01")


def test_a_date_only_text_column_keeps_its_first_and_last_day(tmp_path: Path) -> None:
    """P5 for columns that store dates as text: '2026-08-01' must be counted.

    '2026-08-01' sorts below '2026-08-01 00:00:00' in SQLite, so a
    timestamp-shaped lower bound dropped the first day of every period. The
    CLI fixture caught it, not this file — every row above has a time.
    """
    connection = sqlite3.connect(tmp_path / "dates.db")
    connection.execute("CREATE TABLE users (created_at TEXT, channel TEXT)")
    connection.executemany(
        "INSERT INTO users VALUES (?, 'organic')",
        [("2026-07-31",), ("2026-08-01",), ("2026-08-31",), ("2026-09-01",)],
    )
    connection.commit()
    query = TemplateCompiler({("new_users", "registered"): REGISTERED}).compile(
        _definition(_august())
    )
    try:
        assert connection.execute(query.sql, query.params).fetchone()[0] == 2
    finally:
        connection.close()


def test_an_or_in_a_maintainer_fragment_cannot_escape_the_period(tmp_path: Path) -> None:
    """Unparenthesised, `a OR b AND period` would count every paid row ever."""
    mapping = QueryMapping(
        source="users",
        measure="COUNT(*)",
        label="n",
        time_column="created_at",
        where=("status = 'paid' OR status = 'refunded'", "channel <> 'internal_test'"),
    )
    query = TemplateCompiler({("new_users", "registered"): mapping}).compile(
        _definition(_august())
    )
    assert _count(tmp_path, query) == 2


def test_without_a_period_no_time_condition_is_added(tmp_path: Path) -> None:
    """P9 at the compiler: no period means no window, stated elsewhere, not faked here."""
    query = TemplateCompiler({("new_users", "registered"): REGISTERED}).compile(_definition())
    assert "created_at" not in query.sql
    assert query.params == ()
    assert _count(tmp_path, query) == 4


# ------------------------------------------------------------- P6 refused


def test_a_whole_statement_mapping_refuses_a_period_instead_of_ignoring_it() -> None:
    """P6: running it would answer 「上个月」 with an all-time number."""
    compiler = TemplateCompiler({("new_users", "registered"): "SELECT COUNT(*) FROM users"})
    with pytest.raises(MappingNotFound, match="结构化映射"):
        compiler.compile(_definition(_august()))


def test_a_whole_statement_mapping_still_runs_without_a_period() -> None:
    """The 1A form keeps working where it was ever correct."""
    compiler = TemplateCompiler({("new_users", "registered"): "SELECT COUNT(*) FROM users"})
    assert compiler.compile(_definition()) == CompiledQuery("SELECT COUNT(*) FROM users")


def test_a_mapping_without_a_time_column_refuses_a_period() -> None:
    mapping = QueryMapping(source="users", measure="COUNT(*)", label="n")
    with pytest.raises(MappingNotFound, match="time_column"):
        TemplateCompiler({("new_users", "registered"): mapping}).compile(_definition(_august()))


# ----------------------------------------------------- P7 no user strings


def test_a_period_that_is_not_canonical_is_refused_not_interpolated() -> None:
    """P7: the only way a date reaches SQL is through Period.decode."""
    forged = Rule(PERIOD_RULE_KEY, "2026-08-01..2026-08-31'; DROP TABLE users; --", RuleSource.USER)
    with pytest.raises(WorkflowStateError):
        TemplateCompiler({("new_users", "registered"): REGISTERED}).compile(_definition(forged))


def test_rule_text_from_users_and_documents_never_reaches_the_sql() -> None:
    """P7: explanatory rules are not compiler input at all."""
    query = TemplateCompiler({("new_users", "registered"): REGISTERED}).compile(
        _definition(
            _august(),
            Rule("filters", "x'); DELETE FROM users; --", RuleSource.USER),
            Rule("counting_basis", "UNION SELECT password", RuleSource.DOC, evidence_ref="d#c@0:1"),
        )
    )
    everything = query.sql + " ".join(query.params)
    assert "DELETE" not in everything and "UNION" not in everything


def test_a_variant_value_is_a_lookup_key_never_interpolated() -> None:
    compiler = TemplateCompiler({("new_users", "registered"): REGISTERED})
    with pytest.raises(MappingNotFound):
        compiler.compile(_definition(variant="registered' OR '1'='1"))


# ------------------------------------------------------------- dialects


@pytest.mark.parametrize(
    ("dialect", "alias"),
    [("sqlite", '"新增用户数"'), ("clickhouse", '"新增用户数"'), ("mysql", "`新增用户数`")],
)
def test_the_alias_is_quoted_for_the_dialect(dialect: str, alias: str) -> None:
    query = TemplateCompiler({("new_users", "registered"): REGISTERED}, dialect=dialect).compile(
        _definition()
    )
    assert f"AS {alias}" in query.sql


# ------------------------------------------------------------- loading


def test_structured_and_whole_statement_entries_load_side_by_side(tmp_path: Path) -> None:
    path = tmp_path / "m.yaml"
    path.write_text(
        "mappings:\n"
        "  - metric: new_users\n    variant: registered\n    from: users\n"
        "    measure: COUNT(*)\n    label: 新增用户数\n    time_column: created_at\n"
        "    where: [\"channel <> 'internal_test'\"]\n"
        "  - metric: legacy\n    sql: SELECT 1\n",
        encoding="utf-8",
    )
    table = load_mappings(path)
    assert table[("new_users", "registered")] == REGISTERED
    assert table[("legacy", "")] == "SELECT 1"


@pytest.mark.parametrize(
    ("fields", "complaint"),
    [
        ("    from: users; DROP TABLE users\n    measure: COUNT(*)\n    label: n\n", "from"),
        ("    from: users\n    measure: COUNT(*)\n    label: n\"x\n", "label"),
        (
            "    from: users\n    measure: COUNT(*)\n    label: n\n    time_column: a b\n",
            "time_column",
        ),
        ("    from: users\n    measure: COUNT(*)\n    label: n\n    where: status\n", "where"),
        ("    from: users\n    label: n\n", "measure"),
        ("    sql: SELECT 1\n    from: users\n", "not both"),
    ],
)
def test_malformed_structured_entries_are_refused_at_load(
    tmp_path: Path, fields: str, complaint: str
) -> None:
    path = tmp_path / "m.yaml"
    path.write_text("mappings:\n  - metric: m\n" + fields, encoding="utf-8")
    with pytest.raises(ValueError, match=complaint):
        load_mappings(path)
