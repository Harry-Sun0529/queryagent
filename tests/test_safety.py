"""Table-driven acceptance cases for the SQL safety whitelist (spec §三).

Single SELECT with CTE allowed; DML/DDL, multi-statement, comment-smuggling,
and write-shaped SELECT clauses (INTO OUTFILE / FOR UPDATE) blocked.
"""

from __future__ import annotations

import pytest

from queryagent.errors import SafetyViolation
from queryagent.safety import ensure_safe_select

ALLOWED = [
    "SELECT 1",
    "SELECT id, created_at FROM users",
    "select count(*) from orders where status = 'paid'",
    "WITH recent AS (SELECT * FROM users WHERE created_at >= '2026-06-01') "
    "SELECT count(*) FROM recent",
    "SELECT u.region, count(*) FROM users u JOIN orders o ON o.user_id = u.id "
    "GROUP BY u.region ORDER BY 2 DESC LIMIT 10",
]

BLOCKED = [
    "",
    "   ",
    "INSERT INTO users (id) VALUES (1)",
    "UPDATE users SET region = 'north' WHERE id = 1",
    "DELETE FROM orders WHERE id = 1",
    "DROP TABLE users",
    "ALTER TABLE users ADD COLUMN x INT",
    "TRUNCATE TABLE orders",
    "CREATE TABLE evil (id INT)",
    "GRANT ALL ON *.* TO 'x'@'%'",
    # multi-statement injection (spec acceptance case #3)
    "SELECT 1; DROP TABLE users",
    "SELECT 1;DROP TABLE users;",
    "SELECT 1; SELECT 2",
    # comment smuggling
    "SELECT/**/1;DROP/**/TABLE users",
    "DROP/*harmless?*/TABLE users",
    # write-shaped SELECT clauses
    "SELECT * FROM users INTO OUTFILE '/tmp/x'",
    "SELECT * FROM users FOR UPDATE",
    # not SELECT at all
    "EXPLAIN SELECT 1",
    "SHOW TABLES",
]

MUST_MENTION_REASON = [
    ("SELECT 1; DROP TABLE users", "multiple"),
    ("DROP TABLE users", "SELECT"),
]


@pytest.mark.parametrize(("sql", "fragment"), MUST_MENTION_REASON)
def test_rejection_reasons_are_actionable(sql: str, fragment: str) -> None:
    with pytest.raises(SafetyViolation) as exc_info:
        ensure_safe_select(sql)
    assert fragment.lower() in str(exc_info.value).lower()
    assert exc_info.value.sql == sql


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed(sql: str) -> None:
    ensure_safe_select(sql)  # must not raise


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked(sql: str) -> None:
    with pytest.raises(SafetyViolation):
        ensure_safe_select(sql)
