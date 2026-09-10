"""Placeholder translation for drivers that format rather than bind.

The workflow writes SQL with DB-API ``qmark`` placeholders (``?``): one
neutral form for the compiler, the run record and the safety check. SQLite
binds those natively. PyMySQL and clickhouse-driver do not — both substitute
client-side with ``query % escaped``, so their placeholders are ``%s`` and
``%(name)s``, and *every other* ``%`` in the statement (a maintainer's
``LIKE 'a%'``, a ``DATE_FORMAT(col, '%Y-%m')``) must be doubled or it is read
as a format directive.

Tokenising is what makes that safe. sqlparse is lossless, and a ``?`` inside
a string literal is a String token rather than a placeholder, so it stays as
written; only real placeholders are rewritten.
"""

from __future__ import annotations

import sqlparse
from sqlparse import tokens


def to_pyformat(sql: str, count: int, *, named: bool) -> str:
    """Rewrite ``?`` placeholders for a ``%``-formatting driver.

    Args:
        sql: A statement using ``?`` placeholders.
        count: How many values will be supplied.
        named: ``%(p0)s``-style (clickhouse-driver) instead of ``%s`` (PyMySQL).

    Raises:
        ValueError: The statement's placeholders and the values disagree in
            number. Formatting would fail or, worse, shift a value into the
            wrong position.
    """
    parts: list[str] = []
    seen = 0
    for statement in sqlparse.parse(sql):
        for token in statement.flatten():
            if token.ttype in tokens.Name.Placeholder and token.value == "?":
                parts.append(f"%(p{seen})s" if named else "%s")
                seen += 1
            else:
                parts.append(token.value.replace("%", "%%"))
    if seen != count:
        raise ValueError(f"statement has {seen} placeholders but {count} values were given")
    return "".join(parts)
