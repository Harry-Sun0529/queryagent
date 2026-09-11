"""Totals a maintainer sets and nothing else can raise (slice 1E, ADR-011).

A timeout and a row cap bound one statement. They say nothing about how many
statements one person runs in a day, how many run at once, or how far an
agent explores before it answers. Those totals are counted here.

Two properties this module is built to hold:

1. The limits come from ``config.yaml`` and nowhere else. A ledger reads them
   once, when it is built; nothing a caller passes to ``admit`` can raise
   them, and there is no setter.
2. Admission happens before a statement runs, never after it. A refused
   request has touched the database zero times.

The counts live in the workflow state file, so every process pointed at one
file shares them. Concurrency is a lease with an expiry rather than a counter
in memory: two CLI processes cannot see each other's memory, and a process
killed mid-query must not hold its slot for ever.
"""

from __future__ import annotations

import math
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import TracebackType
from typing import Protocol
from zoneinfo import ZoneInfo

from queryagent.config import BudgetConfig
from queryagent.connectors.base import Connector, QueryResult
from queryagent.errors import QueryAgentError
from queryagent.schema import TableSchema

LEASE_MARGIN_S = 5
"""Seconds a lease outlives the timeouts it covers, for connecting and moving
rows. Past that its holder is presumed dead and the slot is free again."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS budget_leases (
    lease_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS budget_ledger (
    subject_id TEXT NOT NULL,
    day TEXT NOT NULL,
    queries INTEGER NOT NULL DEFAULT 0,
    query_ms INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (subject_id, day)
);
"""


class BudgetExceeded(QueryAgentError):
    """A maintainer-set total refused this request before anything ran.

    ``item`` is the config key that refused it. ``retryable`` is true only
    where waiting minutes helps — a full concurrency slot — and false for a
    spent daily allowance, which a retry loop would only hammer.
    """

    def __init__(self, message: str, *, item: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.item = item
        self.retryable = retryable


class Lease:
    """One admitted request. This base class meters nothing (no budget configured)."""

    def record(self, elapsed_ms: int) -> None:
        """Charge the time one statement took."""

    def refund(self) -> None:
        """Give back the statements reserved but never run."""

    def release(self) -> None:
        """Free the concurrency slot."""

    def __enter__(self) -> Lease:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


class Budget(Protocol):
    """Admits requests against totals: ``SqliteBudgetLedger`` or ``Unmetered``."""

    def admit(self, subject: str, *, queries: int, already: int = 0) -> Lease: ...

    def close(self) -> None: ...


class Unmetered:
    """No ``budget:`` configured: admits everything and records nothing (G1).

    Exists so every caller holds a budget either way and carries no branch
    for its absence — a branch is where "unlimited" and "not checked" would
    drift apart.
    """

    def admit(self, subject: str, *, queries: int, already: int = 0) -> Lease:
        return Lease()

    def close(self) -> None:
        pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteBudgetLedger:
    """Statements and seconds per subject per business day, and leases for concurrency."""

    def __init__(
        self,
        path: str | Path,
        limits: BudgetConfig,
        *,
        statement_timeout_s: int,
        zone: ZoneInfo,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._limits = limits
        self._lease_seconds = statement_timeout_s + LEASE_MARGIN_S
        self._zone = zone
        self._clock = clock
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Wait for another process's admission rather than fail on a locked
        # file: an admission is a handful of statements long.
        self._conn = sqlite3.connect(path, isolation_level=None, timeout=10)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def admit(self, subject: str, *, queries: int, already: int = 0) -> Lease:
        """Reserve ``queries`` statements for ``subject``, or raise BudgetExceeded.

        ``already`` is how many this request has run so far: the agent path
        admits one statement at a time within a question. Checking and
        reserving happen in one ``BEGIN IMMEDIATE`` transaction, so two
        processes cannot both take the last slot or the last statement.
        """
        per_request = self._limits.max_queries_per_request
        if per_request is not None and already + queries > per_request:
            raise BudgetExceeded(
                f"超出预算：本次请求需要执行 {already + queries} 条语句，"
                f"维护者设定每次请求最多 {per_request} 条（budget.max_queries_per_request）",
                item="max_queries_per_request",
            )
        now = self._clock()
        day = now.astimezone(self._zone).date()
        lease_id = uuid.uuid4().hex
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                "DELETE FROM budget_leases WHERE expires_at <= ?", (now.timestamp(),)
            )
            self._check(subject, day, queries, now.timestamp())
            self._conn.execute(
                "INSERT INTO budget_leases VALUES (?,?,?)",
                (lease_id, subject, now.timestamp() + self._lease_seconds * queries),
            )
            self._conn.execute(
                "INSERT INTO budget_ledger (subject_id, day, queries) VALUES (?,?,?) "
                "ON CONFLICT(subject_id, day) DO UPDATE SET queries = queries + excluded.queries",
                (subject, day.isoformat(), queries),
            )
            self._conn.execute("COMMIT")
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        return _LedgerLease(self._conn, lease_id, subject, day.isoformat(), queries)

    def _check(self, subject: str, day: date, queries: int, now: float) -> None:
        limits = self._limits
        if limits.max_concurrent is not None:
            running, soonest = self._conn.execute(
                "SELECT COUNT(*), MIN(expires_at) FROM budget_leases"
            ).fetchone()
            if running >= limits.max_concurrent:
                # E06: say when. A lease's expiry is the latest a slot can take
                # to free up; a request that finishes releases it sooner.
                wait = max(1, math.ceil(soonest - now))
                raise BudgetExceeded(
                    f"超出预算：当前已有 {running} 个请求在执行，维护者设定最多同时 "
                    f"{limits.max_concurrent} 个（budget.max_concurrent）；最迟约 {wait} 秒后"
                    "空出一个（通常更早），稍后重试",
                    item="max_concurrent",
                    retryable=True,
                )
        row = self._conn.execute(
            "SELECT queries, query_ms FROM budget_ledger WHERE subject_id = ? AND day = ?",
            (subject, day.isoformat()),
        ).fetchone()
        used, used_ms = row if row else (0, 0)
        resumes = f"{(day + timedelta(days=1)).isoformat()} 00:00（{self._zone.key}）恢复"
        daily = limits.max_queries_per_day
        if daily is not None and used + queries > daily:
            raise BudgetExceeded(
                f"超出预算：今天已执行 {used} 条语句，本次还需 {queries} 条，"
                f"维护者设定每人每天最多 {daily} 条（budget.max_queries_per_day）；{resumes}",
                item="max_queries_per_day",
            )
        seconds = limits.max_query_seconds_per_day
        if seconds is not None and used_ms >= seconds * 1000:
            raise BudgetExceeded(
                f"超出预算：今天的语句已累计执行 {used_ms / 1000:.1f} 秒，"
                f"维护者设定每人每天最多 {seconds} 秒（budget.max_query_seconds_per_day）；"
                f"{resumes}",
                item="max_query_seconds_per_day",
            )


class _LedgerLease(Lease):
    """A lease held in the ledger: a slot, a reservation, and a day to charge."""

    def __init__(
        self, conn: sqlite3.Connection, lease_id: str, subject: str, day: str, reserved: int
    ) -> None:
        self._conn = conn
        self._lease_id = lease_id
        self._subject = subject
        self._day = day  # the day it was admitted on, even if it runs past midnight
        self._reserved = reserved

    def record(self, elapsed_ms: int) -> None:
        self._conn.execute(
            "UPDATE budget_ledger SET query_ms = query_ms + ? WHERE subject_id = ? AND day = ?",
            (max(elapsed_ms, 0), self._subject, self._day),
        )

    def refund(self) -> None:
        if self._reserved:
            self._conn.execute(
                "UPDATE budget_ledger SET queries = queries - ? WHERE subject_id = ? AND day = ?",
                (self._reserved, self._subject, self._day),
            )
            self._reserved = 0

    def release(self) -> None:
        self._conn.execute("DELETE FROM budget_leases WHERE lease_id = ?", (self._lease_id,))


@contextmanager
def metered(lease: Lease) -> Iterator[None]:
    """Charge the wall time of the block to ``lease``.

    Measured by the client, so it includes the network, and charged even
    when the statement fails: a failed query still spent the database's time.
    """
    started = time.monotonic()
    try:
        yield
    finally:
        lease.record(int((time.monotonic() - started) * 1000))


class BudgetedConnector:
    """A connector whose every statement is admitted by the budget first.

    For the agent path, where the model — not a maintainer mapping — decides
    how many statements a question takes. ``start_request`` marks a new
    question, the unit ``max_queries_per_request`` counts within. Schema
    reads are metadata and pass through uncounted.
    """

    def __init__(self, inner: Connector, budget: Budget, subject: str) -> None:
        self._inner = inner
        self._budget = budget
        self._subject = subject
        self._count = 0
        self.dialect = inner.dialect

    def start_request(self) -> None:
        self._count = 0

    def get_schema(self) -> list[TableSchema]:
        return self._inner.get_schema()

    def execute(
        self, sql: str, *, timeout_s: int, max_rows: int, params: Sequence[object] = ()
    ) -> QueryResult:
        with self._budget.admit(self._subject, queries=1, already=self._count) as lease:
            self._count += 1
            with metered(lease):
                return self._inner.execute(
                    sql, timeout_s=timeout_s, max_rows=max_rows, params=params
                )

    def close(self) -> None:
        self._inner.close()
