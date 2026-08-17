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
