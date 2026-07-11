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
