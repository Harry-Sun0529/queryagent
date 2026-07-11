"""SQL safety layer. **HUMAN-OWNED rule design — spec §〇.**

What belongs here (spec §三 v0.1.0): an sqlparse-based *whitelist* that only
lets through a single SELECT statement (CTEs allowed), and blocks
INSERT / UPDATE / DELETE / DROP / ALTER / TRUNCATE, multi-statement payloads,
and comment-smuggling tricks. Which rules, why, and how the layers stack is
the human's design to own and defend.

Defence in depth (for the rule design to lean on, not replace):
- execution timeout and row caps are enforced at the Connector layer;
- the recommended read-only DB account is the final backstop.

``tests/test_safety.py`` holds the table-driven acceptance cases — remove its
skip marker once implemented. Raise ``SafetyViolation``
(queryagent/errors.py) with a human-readable reason on rejection.
"""

from __future__ import annotations


def ensure_safe_select(sql: str) -> None:
    """Validate that ``sql`` is one safe SELECT statement.

    Raises:
        SafetyViolation: If the statement is not a single, read-only SELECT.

    HUMAN-OWNED: rule design intentionally left to the human author.
    """
    raise NotImplementedError(
        "queryagent/safety.py rules are HUMAN-OWNED (spec §〇): write the whitelist here"
    )
