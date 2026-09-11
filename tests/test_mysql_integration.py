"""Live integration tests against the demo MySQL container (``make demo-up``).

Skipped automatically when the container is not reachable, so CI and
Docker-less machines are unaffected; locally these verify the real
end-to-end path including the read-only-account backstop.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest

from queryagent.connectors.mysql import MySQLConnector
from queryagent.errors import QueryError

DEMO_PORT = 3307


def _reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(DEMO_PORT), reason="demo MySQL not running (make demo-up)"
)


@pytest.fixture(scope="module")
def connector() -> Iterator[MySQLConnector]:
    instance = MySQLConnector(
        host="127.0.0.1",
        port=DEMO_PORT,
        user="queryagent_ro",
        password="demo_ro_password",
        database="demo_shop",
    )
    yield instance
    instance.close()


def test_schema_has_demo_tables_with_metric_seed(connector: MySQLConnector) -> None:
    tables = {t.name: t for t in connector.get_schema()}
    assert {"users", "orders", "order_items", "channels"} <= set(tables)
    users_columns = {c.name: c for c in tables["users"].columns}
    # the metric-ambiguity seed survives the pipeline (spec §五)
    assert users_columns["first_order_at"].nullable is True
    assert "registration" in users_columns["created_at"].comment


def test_demo_row_counts(connector: MySQLConnector) -> None:
    result = connector.execute("SELECT count(*) FROM users", timeout_s=10, max_rows=10)
    assert result.rows == ((50_000,),)


def test_row_cap_truncates(connector: MySQLConnector) -> None:
    result = connector.execute("SELECT id FROM users", timeout_s=10, max_rows=10)
    assert len(result.rows) == 10
    assert result.truncated is True


def test_read_only_account_blocks_writes(connector: MySQLConnector) -> None:
    # Layer-3 defence (SECURITY.md): even without the SQL whitelist, the demo
    # account physically cannot write.
    with pytest.raises(QueryError) as exc_info:
        connector.execute(
            "INSERT INTO users (id, created_at, channel, region) "
            "VALUES (0, NOW(), 'ads', 'north')",
            timeout_s=10,
            max_rows=10,
        )
    assert "denied" in exc_info.value.original_error.lower()


def test_demo_question_has_nontrivial_answer(connector: MySQLConnector) -> None:
    # The v0.1.0 acceptance question must have data behind it (spec §五).
    # Anchored on max(created_at) rather than curdate(): the DB server's
    # clock (Docker VM) need not agree with the host clock that generated
    # the data, and the demo's data-freshness is what is actually asserted.
    result = connector.execute(
        "SELECT date(created_at) AS d, count(*) FROM users "
        "WHERE created_at >= date_sub((SELECT max(created_at) FROM users), INTERVAL 1 MONTH) "
        "GROUP BY d ORDER BY d",
        timeout_s=10,
        max_rows=50,
    )
    assert len(result.rows) >= 28
    assert all(count > 0 for _, count in result.rows)


def test_server_timeout_then_next_query_recovers(connector: MySQLConnector) -> None:
    # A bounded sleep exercises server cancellation without a load-generating join.
    with pytest.raises(QueryError):
        connector.execute('SELECT SUM(SLEEP(0.001)) FROM users', timeout_s=1, max_rows=1)
    assert connector.execute('SELECT 1', timeout_s=1, max_rows=1).rows == ((1,),)


def test_truncation_does_not_poison_next_query(connector: MySQLConnector) -> None:
    result = connector.execute('SELECT id FROM users', timeout_s=1, max_rows=1)
    assert result.truncated and len(result.rows) == 1
    assert connector.execute('SELECT 42', timeout_s=1, max_rows=1).rows == ((42,),)


def test_a_compiled_period_agrees_with_mysqls_own_month_function(
    connector: MySQLConnector,
) -> None:
    """P5 on MySQL: the typed compiler's window against DATE_FORMAT.

    The month is taken from the data rather than hardcoded — demo dates are
    generated relative to the day the container was built.
    """
    import calendar
    from datetime import date

    from queryagent.workflow.compiler import TemplateCompiler
    from queryagent.workflow.mappings import QueryMapping
    from queryagent.workflow.models import PERIOD_RULE_KEY, BusinessDefinition, Rule, RuleSource

    month = connector.execute(
        "SELECT DATE_FORMAT(MAX(created_at), '%Y-%m') FROM users", timeout_s=10, max_rows=1
    ).rows[0][0]
    year, number = (int(part) for part in month.split("-"))
    last = calendar.monthrange(year, number)[1]
    period = f"{date(year, number, 1)}..{date(year, number, last)}"
    compiler = TemplateCompiler(
        {
            ("new_users", "registered"): QueryMapping(
                source="users",
                measure="COUNT(*)",
                label="新增用户数",
                time_column="created_at",
                where=("channel <> 'internal_test'",),
            )
        },
        dialect="mysql",
    )
    definition = BusinessDefinition(
        metric="new_users",
        display_name="新增用户",
        rules=(
            Rule("variant", "registered", RuleSource.USER),
            Rule(PERIOD_RULE_KEY, period, RuleSource.USER),
        ),
    )
    query = compiler.compile(definition)
    assert query.params and "20" not in query.sql  # F1: the dates are bound, not text
    compiled = connector.execute(query.sql, timeout_s=10, max_rows=1, params=query.params)
    native = connector.execute(
        "SELECT COUNT(*) FROM users WHERE channel <> 'internal_test' "
        f"AND DATE_FORMAT(created_at, '%Y-%m') = '{month}'",
        timeout_s=10,
        max_rows=1,
    )
    assert compiled.rows == native.rows
    assert compiled.rows[0][0] > 0


def test_a_percent_sign_in_the_statement_survives_bound_values(
    connector: MySQLConnector,
) -> None:
    """F2: PyMySQL formats with `%`, so a LIKE pattern must reach the server intact."""
    bound = connector.execute(
        "SELECT COUNT(*) FROM users WHERE channel LIKE '%rgan%' AND created_at >= ?",
        timeout_s=10,
        max_rows=1,
        params=("2026-08-01",),
    )
    native = connector.execute(
        "SELECT COUNT(*) FROM users WHERE channel = 'organic' AND created_at >= '2026-08-01'",
        timeout_s=10,
        max_rows=1,
    )
    assert bound.rows == native.rows
    assert bound.rows[0][0] > 0


def test_the_freshness_probe_reads_as_the_newest_records_date(connector: MySQLConnector) -> None:
    """T37: MySQL returns a datetime; it must come out as the same day DATE() gives."""
    from queryagent.workflow.compiler import TemplateCompiler
    from queryagent.workflow.coverage import latest_date
    from queryagent.workflow.mappings import QueryMapping
    from queryagent.workflow.models import BusinessDefinition

    compiler = TemplateCompiler(
        {("gmv", ""): QueryMapping("orders", "SUM(amount)", "成交额", time_column="created_at")},
        dialect="mysql",
    )
    probe = compiler.freshness_probe(BusinessDefinition(metric="gmv", display_name="成交额"))
    assert probe is not None
    probed = connector.execute(probe.sql, timeout_s=10, max_rows=1).rows[0][0]
    native = connector.execute(
        "SELECT DATE(MAX(created_at)) FROM orders", timeout_s=10, max_rows=1
    ).rows[0][0]
    assert latest_date(probed) == native


@pytest.mark.parametrize(
    ("grain", "native_key"),
    [
        ("day", "DATE_FORMAT(created_at, '%Y-%m-%d')"),
        ("week", "YEARWEEK(created_at, 3)"),  # mode 3: weeks start on Monday
        ("month", "DATE_FORMAT(created_at, '%Y-%m')"),
    ],
)
def test_each_time_grain_agrees_with_mysqls_own_functions(
    connector: MySQLConnector, grain: str, native_key: str
) -> None:
    """F8 on MySQL: the compiled grain expressions against independent native ones."""
    import calendar
    from datetime import date

    from queryagent.workflow.compiler import TemplateCompiler
    from queryagent.workflow.mappings import QueryMapping
    from queryagent.workflow.models import (
        GROUP_RULE_KEY,
        PERIOD_RULE_KEY,
        BusinessDefinition,
        Rule,
        RuleSource,
    )

    month = connector.execute(
        "SELECT DATE_FORMAT(MAX(created_at), '%Y-%m') FROM users", timeout_s=10, max_rows=1
    ).rows[0][0]
    year, number = (int(part) for part in month.split("-"))
    period = f"{date(year, number, 1)}..{date(year, number, calendar.monthrange(year, number)[1])}"
    mapping = QueryMapping(
        "users", "COUNT(*)", "新增用户数", "created_at", ("channel <> 'internal_test'",)
    )
    definition = BusinessDefinition(
        metric="new_users",
        display_name="新增用户",
        rules=(
            Rule("variant", "registered", RuleSource.USER),
            Rule(PERIOD_RULE_KEY, period, RuleSource.USER),
            Rule(GROUP_RULE_KEY, grain, RuleSource.USER),
        ),
    )
    query = TemplateCompiler({("new_users", "registered"): mapping}, dialect="mysql").compile(
        definition
    )
    compiled = connector.execute(query.sql, timeout_s=10, max_rows=100, params=query.params)
    native = connector.execute(
        f"SELECT {native_key} AS k, COUNT(*) FROM users WHERE channel <> 'internal_test' "
        f"AND DATE_FORMAT(created_at, '%Y-%m') = '{month}' GROUP BY k ORDER BY k",
        timeout_s=10,
        max_rows=100,
    )
    assert [row[1] for row in compiled.rows] == [row[1] for row in native.rows]
    if grain == "day":
        assert [str(row[0]) for row in compiled.rows] == [row[0] for row in native.rows]


def test_a_value_filter_agrees_with_a_literal_where_on_mysql(connector: MySQLConnector) -> None:
    """G17 on MySQL: the bound channel against a written-out one, alone and split by day."""
    import calendar
    from datetime import date

    from queryagent.workflow.compiler import TemplateCompiler
    from queryagent.workflow.grouping import Dimension
    from queryagent.workflow.mappings import QueryMapping
    from queryagent.workflow.models import (
        FILTER_RULE_KEY,
        GROUP_RULE_KEY,
        PERIOD_RULE_KEY,
        BusinessDefinition,
        Rule,
        RuleSource,
    )

    month = connector.execute(
        "SELECT DATE_FORMAT(MAX(created_at), '%Y-%m') FROM users", timeout_s=10, max_rows=1
    ).rows[0][0]
    year, number = (int(part) for part in month.split("-"))
    period = f"{date(year, number, 1)}..{date(year, number, calendar.monthrange(year, number)[1])}"
    compiler = TemplateCompiler(
        {("new_users", "registered"): QueryMapping("users", "COUNT(*)", "n", "created_at")},
        dialect="mysql",
        dimensions=(
            Dimension("channel", "渠道", columns=(("users", "channel"),), values=(("ads", ()),)),
        ),
    )
    rules = (
        Rule("variant", "registered", RuleSource.USER),
        Rule(PERIOD_RULE_KEY, period, RuleSource.USER),
        Rule(FILTER_RULE_KEY, "dim:channel=ads", RuleSource.USER),
    )
    total = compiler.compile(BusinessDefinition("new_users", "新增用户", rules=rules))
    daily = compiler.compile(
        BusinessDefinition(
            "new_users", "新增用户", rules=(*rules, Rule(GROUP_RULE_KEY, "day", RuleSource.USER))
        )
    )
    native = connector.execute(
        f"SELECT COUNT(*) FROM users WHERE channel = 'ads' "
        f"AND DATE_FORMAT(created_at, '%Y-%m') = '{month}'",
        timeout_s=10,
        max_rows=1,
    ).rows[0][0]
    compiled = connector.execute(total.sql, timeout_s=10, max_rows=1, params=total.params)
    by_day = connector.execute(daily.sql, timeout_s=10, max_rows=100, params=daily.params)
    assert compiled.rows[0][0] == native > 0
    assert sum(row[1] for row in by_day.rows) == native
