"""Exception hierarchy (spec §二). Frozen from v0.1.0 on: only additions allowed."""

from __future__ import annotations


class QueryAgentError(Exception):
    """Base class for all QueryAgent errors."""


class SafetyViolation(QueryAgentError):
    """The safety layer rejected a SQL statement.

    Attributes:
        reason: Human-readable explanation of why the statement was blocked.
        sql: The offending SQL text.
    """

    def __init__(self, reason: str, sql: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.sql = sql


class ToolValidationError(QueryAgentError):
    """Tool argument validation failed.

    Usually converted into an error Observation and fed back to the model
    rather than propagated (model-hallucination tolerance, spec §二).
    """


class LLMParseError(QueryAgentError):
    """The model output could not be parsed into a usable action."""


class ConnectorError(QueryAgentError):
    """Base class for data source errors."""


class QueryError(ConnectorError):
    """A query failed at the database.

    Carries the dialect's original error text so the agent can feed it back to
    the model for self-correction (spec §二).

    Attributes:
        dialect: The connector dialect that produced the error (e.g. "mysql").
        original_error: The raw error text from the database driver.
    """

    def __init__(self, message: str, *, dialect: str) -> None:
        super().__init__(message)
        self.dialect = dialect
        self.original_error = message
