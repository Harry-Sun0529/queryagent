"""Binding the workflow's executor to a real connector.

Kept separate from :mod:`queryagent.workflow.service` so the service can be
tested against a counting double: most of slice 1A's assertions are about
queries that must *not* happen, and those are only credible when the thing
being counted is the same seam production uses.

The safety check stays even though slice 1A only executes maintainer-written
templates. Defence here is cheap, and 1C will start generating statements.
"""

from __future__ import annotations

from collections.abc import Callable

from queryagent import safety
from queryagent.connectors.base import Connector, QueryResult
from queryagent.workflow.compiler import CompiledQuery


def make_connector_executor(
    connector: Connector, *, timeout_s: int, max_rows: int
) -> Callable[[CompiledQuery], QueryResult]:
    """Return the executor the workflow calls once a run is authorised.

    The safety check reads the statement with its placeholders — the text
    that is sent — and the values go to the driver, not into the text.
    """

    def execute(query: CompiledQuery) -> QueryResult:
        safety.ensure_safe_select(query.sql)
        return connector.execute(
            query.sql, timeout_s=timeout_s, max_rows=max_rows, params=query.params
        )

    return execute
