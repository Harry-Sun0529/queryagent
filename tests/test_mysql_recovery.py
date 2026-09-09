"""MySQL driver failures exercised through the Connector contract, without a server."""

from unittest.mock import Mock

import pymysql
import pytest

from queryagent.connectors.mysql import MySQLConnector
from queryagent.errors import QueryError


def connection():
    conn = Mock()
    conn.open = True
    conn.close.side_effect = lambda: setattr(conn, "open", False)
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.description = [("value",)]
    cursor.fetchmany.return_value = [(1,)]
    conn.cursor.return_value = cursor
    return conn, cursor


def connector(**kwargs):
    return MySQLConnector(
        host="example",
        port=3306,
        user="readonly",
        password="",
        database="demo",
        pool_size=1,
        connect_timeout_s=1,
        **kwargs,
    )


def test_refused_timeout_never_runs_business_sql(monkeypatch):
    conn, cursor = connection()
    cursor.execute.side_effect = [pymysql.OperationalError("timeout rejected"), None]
    monkeypatch.setattr(pymysql, "connect", lambda **_: conn)
    db = connector()
    try:
        with pytest.raises(QueryError, match="timeout rejected"):
            db.execute("SELECT 1", timeout_s=1, max_rows=1)
        assert all(call.args[0] != "SELECT 1" for call in cursor.execute.call_args_list)
    finally:
        db.close()


def test_reconnect_failure_does_not_exhaust_pool(monkeypatch):
    old, _ = connection()
    new, _ = connection()
    old.ping.side_effect = [None, pymysql.OperationalError("stale")]
    connect = Mock(side_effect=[old, pymysql.OperationalError("offline"), new])
    monkeypatch.setattr(pymysql, "connect", connect)
    # Bound a queue wait in the broken implementation so this regression cannot hang CI.
    import queue

    original_get = queue.LifoQueue.get
    monkeypatch.setattr(
        queue.LifoQueue,
        "get",
        lambda self, block=True, timeout=None: original_get(
            self, block=block, timeout=timeout if timeout else 0.05
        ),
    )
    db = connector()
    try:
        assert db.execute("SELECT 1", timeout_s=1, max_rows=1).rows == ((1,),)
        with pytest.raises(QueryError, match="offline"):
            db.execute("SELECT 1", timeout_s=1, max_rows=1)
        assert db.execute("SELECT 1", timeout_s=1, max_rows=1).rows == ((1,),)
    finally:
        db.close()


def test_truncated_stream_discards_connection_without_draining(monkeypatch):
    old, cursor = connection()
    fresh, _ = connection()
    cursor.fetchmany.return_value = [(1,), (2,)]
    connect = Mock(side_effect=[old, fresh])
    monkeypatch.setattr(pymysql, "connect", connect)
    db = connector()
    try:
        result = db.execute("SELECT value FROM big_table", timeout_s=1, max_rows=1)
        assert result.rows == ((1,),) and result.truncated
        old.cursor.assert_called_with(pymysql.cursors.SSCursor)
        cursor.fetchmany.assert_called_once_with(2)
        cursor.close.assert_not_called()  # SSCursor.close would drain all unread rows
        assert not old.open
        assert db.execute("SELECT 1", timeout_s=1, max_rows=1).rows == ((1,),)
        assert connect.call_count == 2
    finally:
        db.close()


def test_waiting_borrower_can_use_discarded_capacity(monkeypatch):
    import queue
    from threading import Event, Thread

    waiting, release = Event(), Event()
    old, cursor = connection()
    fresh, _ = connection()
    original_get = queue.LifoQueue.get

    def observe_wait(self, block=True, timeout=None):
        if block:
            waiting.set()
        return original_get(self, block=block, timeout=timeout)

    monkeypatch.setattr(queue.LifoQueue, 'get', observe_wait)
    def fetch(_):
        assert release.wait(3)
        return [(1,), (2,)]
    cursor.fetchmany.side_effect = fetch
    monkeypatch.setattr(pymysql, 'connect', Mock(side_effect=[old, fresh]))
    db = connector()
    outcomes = []
    def query():
        try:
            outcomes.append(db.execute('SELECT 1', timeout_s=1, max_rows=1).rows)
        except QueryError as exc:
            outcomes.append(str(exc))
    first, second = Thread(target=query), Thread(target=query)
    first.start()
    second.start()
    try:
        assert waiting.wait(2)
    finally:
        release.set()
        first.join(3)
        second.join(3)
        db.close()
    assert outcomes == [((1,),), ((1,),)]
