"""Tool registry and the built-in ``get_schema`` / ``execute_sql`` tools.

Design note (spec §二): validation failures never raise to the agent loop.
They come back as error ``Observation`` objects that are fed to the model —
this is the model-hallucination tolerance mechanism. The one deliberate
exception is ``SafetyViolation``: it propagates, because it is an agent
termination condition (a model that just tried to write data should not get
another attempt this run), not a retryable mistake.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from queryagent import safety
from queryagent.connectors.base import Connector, QueryResult
from queryagent.errors import QueryError, ToolValidationError
from queryagent.schema import render_schema


@dataclass(frozen=True)
class ToolSpec:
    """One callable tool: JSON-Schema-described input, str-returning handler."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., str]


@dataclass(frozen=True)
class Observation:
    """What the model sees after a tool call (success or converted failure)."""

    content: str
    is_error: bool = False


_JSON_TO_PY: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


class ToolRegistry:
    """Validates model-proposed tool calls and dispatches them to handlers."""

    def __init__(self, specs: Iterable[ToolSpec] = ()) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        """Add a tool; duplicate names are a programming error and raise."""
        if spec.name in self._specs:
            raise ValueError(f"duplicate tool name: {spec.name}")
        self._specs[spec.name] = spec

    def specs(self) -> tuple[ToolSpec, ...]:
        """Return registered tools, for passing to ``LLMBackend.complete``."""
        return tuple(self._specs.values())

    def validate_and_dispatch(self, name: str, raw_args: dict[str, Any]) -> Observation:
        """Validate a proposed call and run it; failures become Observations.

        Args:
            name: Tool name as proposed by the model.
            raw_args: Raw arguments as proposed by the model.

        Returns:
            The handler's output, or an error Observation describing what was
            wrong so the model can repair its call.

        Raises:
            SafetyViolation: Deliberately not converted — see note below.
        """
        spec = self._specs.get(name)
        if spec is None:
            available = ", ".join(sorted(self._specs)) or "(none)"
            return Observation(f"Unknown tool '{name}'. Available tools: {available}.", True)
        errors = _validate_args(spec.input_schema, raw_args)
        if errors:
            # The error echoes the full expected schema back to the model:
            # tokens are spent only on the (rare) miss path, and the schema is
            # exactly what the model needs to repair the call in one shot.
            detail = "; ".join(errors)
            return Observation(
                f"Invalid arguments for '{name}': {detail}. Expected schema: {spec.input_schema}",
                True,
            )
        try:
            return Observation(spec.handler(**raw_args))
        except QueryError as exc:
            # Original dialect error text fed back verbatim — this is the fuel
            # for the v0.1.1 self-correction loop (spec §三).
            return Observation(f"Query failed ({exc.dialect}): {exc.original_error}", True)
        except ToolValidationError as exc:
            return Observation(str(exc), True)
        # SafetyViolation (and any unexpected exception) deliberately
        # propagates — see the module docstring.


def _validate_args(schema: dict[str, Any], raw_args: Any) -> list[str]:
    """Check raw args against a JSON-Schema subset; return error strings."""
    if not isinstance(raw_args, dict):
        return [f"arguments must be an object, got {type(raw_args).__name__}"]
    properties: dict[str, Any] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])
    errors = [f"missing required argument '{key}'" for key in required if key not in raw_args]
    for key, value in raw_args.items():
        if key not in properties:
            # Unknown arguments are rejected (strict) rather than dropped:
            # a hallucinated argument usually means the model misread the
            # tool contract, and silence would mask that.
            errors.append(f"unknown argument '{key}'")
            continue
        expected = properties[key].get("type")
        py_type = _JSON_TO_PY.get(expected) if expected else None
        if py_type is None:
            continue
        if expected in ("integer", "number") and isinstance(value, bool):
            errors.append(f"argument '{key}' must be {expected}, got boolean")
        elif not isinstance(value, py_type):
            errors.append(f"argument '{key}' must be {expected}, got {type(value).__name__}")
    return errors


def make_default_tools(connector: Connector, *, timeout_s: int, max_rows: int) -> list[ToolSpec]:
    """Build the v0.1.0 minimal toolset bound to ``connector`` (spec §三).

    Args:
        connector: The active data source.
        timeout_s: Per-query timeout enforced at the connector layer.
        max_rows: Row cap enforced at the connector layer.

    Returns:
        ``get_schema`` and ``execute_sql`` tool specs.
    """

    def get_schema_handler() -> str:
        return render_schema(connector.get_schema())

    def execute_sql_handler(sql: str) -> str:
        safety.ensure_safe_select(sql)
        result = connector.execute(sql, timeout_s=timeout_s, max_rows=max_rows)
        return format_query_result(result)

    return [
        ToolSpec(
            name="get_schema",
            description=(
                "Return the schema (tables, columns, types, comments) of the connected database."
            ),
            input_schema={"type": "object", "properties": {}, "required": []},
            handler=get_schema_handler,
        ),
        ToolSpec(
            name="execute_sql",
            description=(
                f"Execute one read-only SELECT statement ({connector.dialect} dialect) and "
                f"return the resulting rows. Results are capped at {max_rows} rows."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A single SELECT statement (CTEs allowed).",
                    }
                },
                "required": ["sql"],
            },
            handler=execute_sql_handler,
        ),
    ]


CLARIFY_TOOL_NAME = "ask_clarification"


def make_clarify_tool() -> ToolSpec:
    """The clarification tool (spec §三 v0.2.0).

    Registered only when the metric store carries caution-flagged metrics.
    The agent loop intercepts calls to it *before* dispatch and converts
    them into a terminal ``ClarifyEvent`` — the handler below never runs in
    normal operation and exists to satisfy the ToolSpec contract.
    """
    return ToolSpec(
        name=CLARIFY_TOOL_NAME,
        description=(
            "Ask the user ONE short clarifying question. Use ONLY when matched "
            "business metrics carry a caution about competing definitions AND "
            "the user's question does not say which definition to use AND the "
            "choice changes the SQL. If the question already disambiguates, or "
            "no caution applies, do NOT call this — answer directly."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The clarifying question to show the user, in their language.",
                },
                "metrics": {
                    "type": "array",
                    "description": "Names of the conflicting metrics (e.g. ['new_users']).",
                },
            },
            "required": ["question", "metrics"],
        },
        handler=lambda question, metrics: "",  # intercepted by the agent loop
    )


def format_query_result(result: QueryResult) -> str:
    """Format a QueryResult as plain text for the model to read."""
    header = " | ".join(result.columns)
    lines = [header, "-" * min(len(header), 80)]
    for row in result.rows:
        lines.append(" | ".join("NULL" if value is None else str(value) for value in row))
    footer = f"({len(result.rows)} rows, {result.elapsed_ms} ms"
    footer += ", truncated)" if result.truncated else ")"
    lines.append(footer)
    return "\n".join(lines)
