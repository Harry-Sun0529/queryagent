"""SQL safety layer: a whitelist, not a blacklist.

Only statements that can be *proven* to be a single read-only SELECT (CTEs
allowed) pass; everything else is rejected. Naive regex filtering fails both
ways — ``WHERE note = 'delete me'`` is a legal query, and ``DROP/*x*/TABLE``
sails past substring checks — so the checks below operate on sqlparse's
token stream, never on raw text.

Three stacked checks (each assumes the previous one can be fooled):
1. exactly one non-blank statement — kills ``SELECT 1; DROP TABLE users``
   and every comment-smuggled multi-statement variant;
2. the first meaningful token must be SELECT or WITH, and sqlparse's
   statement type must agree — kills plain DML/DDL, EXPLAIN, SHOW, etc.;
3. no forbidden keyword anywhere in the token stream — kills writes hidden
   inside an otherwise SELECT-shaped statement (subquery tricks,
   ``INTO OUTFILE`` file writes, ``FOR UPDATE`` locking).

This layer is one of three (SECURITY.md): connector-level timeout/row caps
and the read-only database account back it up independently.
"""

from __future__ import annotations

import sqlparse
from sqlparse import tokens as T
from sqlparse.sql import Statement

from queryagent.errors import SafetyViolation

_ALLOWED_FIRST_TOKENS = {"SELECT", "WITH"}
_ALLOWED_STATEMENT_TYPES = {"SELECT"}

# Keywords that must never appear anywhere in an allowed statement. Matched
# against Keyword-typed tokens only, so string literals and quoted
# identifiers never trigger them. UPDATE also covers ``SELECT ... FOR
# UPDATE`` (lock acquisition); INTO covers ``INTO OUTFILE``/``INTO
# DUMPFILE``/``SELECT INTO`` (file/variable writes).
_FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "REPLACE", "MERGE", "GRANT", "REVOKE", "SET", "USE", "CALL", "EXEC",
    "EXECUTE", "PREPARE", "DEALLOCATE", "LOCK", "UNLOCK", "RENAME", "KILL",
    "SHUTDOWN", "LOAD", "HANDLER", "IMPORT", "INTO", "OUTFILE", "DUMPFILE",
    "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX",
}


def ensure_safe_select(sql: str) -> None:
    """Validate that ``sql`` is one safe SELECT statement.

    Args:
        sql: Raw SQL text as proposed by the model.

    Raises:
        SafetyViolation: With a human-readable reason, if the statement is
            not a single read-only SELECT.
    """
    if not sql or not sql.strip():
        raise SafetyViolation("empty SQL statement", sql)
    statements = [s for s in sqlparse.parse(sql) if not _is_blank(s)]
    if not statements:
        raise SafetyViolation("no SQL statement found", sql)
    if len(statements) > 1:
        raise SafetyViolation(
            f"multiple SQL statements are not allowed ({len(statements)} found); "
            "send exactly one SELECT",
            sql,
        )
    statement = statements[0]

    first = statement.token_first(skip_cm=True)
    first_value = (first.normalized or "").upper() if first is not None else ""
    if first_value not in _ALLOWED_FIRST_TOKENS:
        raise SafetyViolation(
            f"only SELECT statements are allowed (statement starts with "
            f"'{first_value or '?'}')",
            sql,
        )
    statement_type = statement.get_type()
    if statement_type not in _ALLOWED_STATEMENT_TYPES:
        raise SafetyViolation(
            f"only SELECT statements are allowed (parsed as '{statement_type}')", sql
        )

    forbidden = _forbidden_keywords(statement)
    if forbidden:
        raise SafetyViolation(
            f"forbidden keyword(s) in statement: {', '.join(sorted(forbidden))}", sql
        )


def _is_blank(statement: Statement) -> bool:
    """True for statements that are only whitespace, comments or semicolons."""
    for token in statement.flatten():
        if token.is_whitespace:
            continue
        if token.ttype in T.Comment:
            continue
        if token.ttype in T.Punctuation and token.value == ";":
            continue
        return False
    return True


def _forbidden_keywords(statement: Statement) -> set[str]:
    """Collect forbidden keywords from Keyword-typed tokens only."""
    found: set[str] = set()
    for token in statement.flatten():
        if token.ttype is None or token.ttype not in T.Keyword:
            continue
        value = token.normalized.upper()
        if value in _FORBIDDEN_KEYWORDS:
            found.add(value)
    return found
