"""Live integration tests against the demo ClickHouse container.

Start it with ``make demo-up-ch``. Skipped when the container is not
reachable or clickhouse-driver is not installed (it is an optional extra).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest

pytest.importorskip("clickhouse_driver")

from queryagent.connectors.clickhouse import ClickHouseConnector  # noqa: E402
from queryagent.errors import QueryError  # noqa: E402

DEMO_PORT = 9001


def _reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(DEMO_PORT), reason="demo ClickHouse not running (make demo-up-ch)"
)


@pytest.fixture(scope="module")
def connector() -> Iterator[ClickHouseConnector]:
    instance = ClickHouseConnector(
        host="127.0.0.1",
        port=DEMO_PORT,
        user="demo",
        password="demo_ch_password",
        database="demo_shop",
    )
    yield instance
    instance.close()


def test_schema_has_demo_tables(connector: ClickHouseConnector) -> None:
    tables = {t.name: t for t in connector.get_schema()}
    assert {"users", "orders", "order_items", "channels"} <= set(tables)
    users_columns = {c.name: c for c in tables["users"].columns}
    assert users_columns["first_order_at"].nullable is True  # Nullable(DateTime)
    assert users_columns["id"].nullable is False


def test_demo_row_counts(connector: ClickHouseConnector) -> None:
    result = connector.execute("SELECT count(*) FROM users", timeout_s=10, max_rows=10)
    assert result.rows == ((50_000,),)


def test_row_cap_truncates(connector: ClickHouseConnector) -> None:
    result = connector.execute("SELECT id FROM users", timeout_s=10, max_rows=10)
    assert len(result.rows) == 10
    assert result.truncated is True


def test_error_wrapped_with_dialect(connector: ClickHouseConnector) -> None:
    with pytest.raises(QueryError) as exc_info:
        connector.execute("SELECT * FROM missing_table", timeout_s=10, max_rows=10)
    assert exc_info.value.dialect == "clickhouse"


def test_a_compiled_period_agrees_with_clickhouses_own_month_function(
    connector: ClickHouseConnector,
) -> None:
    """P5 on ClickHouse: string bounds against a DateTime column, versus toYYYYMM."""
    import calendar
    from datetime import date

    from queryagent.workflow.compiler import TemplateCompiler
    from queryagent.workflow.mappings import QueryMapping
    from queryagent.workflow.models import PERIOD_RULE_KEY, BusinessDefinition, Rule, RuleSource

    stamp = connector.execute(
        "SELECT toYYYYMM(max(created_at)) FROM users", timeout_s=10, max_rows=1
    ).rows[0][0]
    year, number = divmod(int(stamp), 100)
    last = calendar.monthrange(year, number)[1]
    period = f"{date(year, number, 1)}..{date(year, number, last)}"
    compiler = TemplateCompiler(
        {
            ("new_users", "registered"): QueryMapping(
                source="users",
                measure="count()",
                label="新增用户数",
                time_column="created_at",
                where=("channel != 'internal_test'",),
            )
        },
        dialect="clickhouse",
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
        "SELECT count() FROM users WHERE channel != 'internal_test' "
        f"AND toYYYYMM(created_at) = {stamp}",
        timeout_s=10,
        max_rows=1,
    )
    assert compiled.rows == native.rows
    assert compiled.rows[0][0] > 0


def test_a_percent_sign_in_the_statement_survives_bound_values(
    connector: ClickHouseConnector,
) -> None:
    """F2: clickhouse-driver formats with `%`, so a LIKE pattern must reach the server intact."""
    bound = connector.execute(
        "SELECT count() FROM users WHERE channel LIKE '%rgan%' AND created_at >= ?",
        timeout_s=10,
        max_rows=1,
        params=("2026-08-01",),
    )
    native = connector.execute(
        "SELECT count() FROM users WHERE channel = 'organic' AND created_at >= '2026-08-01'",
        timeout_s=10,
        max_rows=1,
    )
    assert bound.rows == native.rows
    assert bound.rows[0][0] > 0


def test_the_freshness_probe_reads_as_the_newest_records_date(
    connector: ClickHouseConnector,
) -> None:
    """T37: ClickHouse returns a datetime; it must come out as the day toDate() gives."""
    from queryagent.workflow.compiler import TemplateCompiler
    from queryagent.workflow.coverage import latest_date
    from queryagent.workflow.mappings import QueryMapping
    from queryagent.workflow.models import BusinessDefinition

    compiler = TemplateCompiler(
        {("gmv", ""): QueryMapping("orders", "sum(amount)", "成交额", time_column="created_at")},
        dialect="clickhouse",
    )
    probe = compiler.freshness_probe(BusinessDefinition(metric="gmv", display_name="成交额"))
    assert probe is not None
    probed = connector.execute(probe.sql, timeout_s=10, max_rows=1).rows[0][0]
    native = connector.execute(
        "SELECT toDate(max(created_at)) FROM orders", timeout_s=10, max_rows=1
    ).rows[0][0]
    assert latest_date(probed) == native
