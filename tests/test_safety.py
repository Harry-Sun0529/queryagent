"""Table-driven acceptance cases for the SQL safety whitelist (spec §三).

The rule design is HUMAN-OWNED; this table encodes the spec's acceptance
criteria (single SELECT with CTE allowed; DML/DDL, multi-statement and
comment-smuggling blocked). Remove the module-level skip once
queryagent/safety.py is implemented. Adjusting borderline cases is the rule
owner's call — with a rationale per change.
"""

from __future__ import annotations

import pytest

from queryagent.errors import SafetyViolation
from queryagent.safety import ensure_safe_select

pytestmark = pytest.mark.skip(
    reason="safety.py rules are HUMAN-OWNED and not implemented yet; remove once rules land"
)

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
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allowed(sql: str) -> None:
    ensure_safe_select(sql)  # must not raise


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked(sql: str) -> None:
    with pytest.raises(SafetyViolation):
        ensure_safe_select(sql)
