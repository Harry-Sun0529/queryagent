"""Unit tests for the tool registry validation/dispatch policy."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from queryagent.connectors.base import QueryResult
from queryagent.errors import QueryError, SafetyViolation
from queryagent.tools import Observation, ToolRegistry, ToolSpec, format_query_result


def echo_spec(handler: Callable[..., str] | None = None) -> ToolSpec:
    return ToolSpec(
        name="echo",
        description="Echo a message.",
        input_schema={
            "type": "object",
            "properties": {"msg": {"type": "string"}, "times": {"type": "integer"}},
            "required": ["msg"],
        },
        handler=handler or (lambda msg, times=1: msg * times),
    )


def test_dispatch_ok() -> None:
    registry = ToolRegistry([echo_spec()])
    assert registry.validate_and_dispatch("echo", {"msg": "hi", "times": 2}) == Observation("hihi")


def test_unknown_tool_becomes_error_observation() -> None:
    registry = ToolRegistry([echo_spec()])
    obs = registry.validate_and_dispatch("run_python", {})
    assert obs.is_error
    assert "echo" in obs.content  # available tools are listed for the model


def test_missing_required_argument() -> None:
    calls: list[str] = []
    registry = ToolRegistry([echo_spec(lambda msg, times=1: calls.append(msg) or "x")])
    obs = registry.validate_and_dispatch("echo", {"times": 2})
    assert obs.is_error
    assert "msg" in obs.content
    assert calls == []  # handler must not run on invalid input


def test_wrong_type() -> None:
    registry = ToolRegistry([echo_spec()])
    obs = registry.validate_and_dispatch("echo", {"msg": 5})
    assert obs.is_error
    assert "string" in obs.content


def test_bool_is_not_an_integer() -> None:
    registry = ToolRegistry([echo_spec()])
    obs = registry.validate_and_dispatch("echo", {"msg": "x", "times": True})
    assert obs.is_error


def test_unknown_argument_rejected() -> None:
    registry = ToolRegistry([echo_spec()])
    obs = registry.validate_and_dispatch("echo", {"msg": "x", "extra": 1})
    assert obs.is_error
    assert "extra" in obs.content


def test_non_object_arguments() -> None:
    registry = ToolRegistry([echo_spec()])
    obs = registry.validate_and_dispatch("echo", "just a string")  # type: ignore[arg-type]
    assert obs.is_error


def test_query_error_becomes_observation_with_original_text() -> None:
    def failing(msg: str, times: int = 1) -> str:
        raise QueryError("Unknown column 'foo' in 'field list'", dialect="mysql")

    registry = ToolRegistry([echo_spec(failing)])
    obs = registry.validate_and_dispatch("echo", {"msg": "x"})
    assert obs.is_error
    assert "Unknown column 'foo'" in obs.content  # verbatim, fuel for self-repair
    assert "mysql" in obs.content


def test_safety_violation_propagates() -> None:
    def blocked(msg: str, times: int = 1) -> str:
        raise SafetyViolation("only SELECT allowed", sql=msg)

    registry = ToolRegistry([echo_spec(blocked)])
    with pytest.raises(SafetyViolation):
        registry.validate_and_dispatch("echo", {"msg": "DROP TABLE users"})


def test_duplicate_registration_raises() -> None:
    registry = ToolRegistry([echo_spec()])
    with pytest.raises(ValueError):
        registry.register(echo_spec())


def test_format_query_result_truncation_marker() -> None:
    result = QueryResult(
        columns=("id", "name"),
        rows=((1, "a"), (2, None)),
        elapsed_ms=12,
        truncated=True,
    )
    text = format_query_result(result)
    assert "id | name" in text
    assert "NULL" in text
    assert "truncated" in text


def wide_result(rows: int, cell_chars: int) -> QueryResult:
    return QueryResult(
        columns=("a", "b"),
        rows=tuple(("x" * cell_chars, "y" * cell_chars) for _ in range(rows)),
        elapsed_ms=1,
        truncated=False,
    )


def test_observation_is_bounded_regardless_of_cell_width() -> None:
    # A row cap alone cannot bound the observation: 200 rows of long text
    # columns produced ~50k tokens, which blew the context budget and got the
    # whole result dropped by trimming.
    text = format_query_result(wide_result(rows=200, cell_chars=200))
    assert len(text) <= 12_000


def test_bounded_output_says_it_was_shortened() -> None:
    text = format_query_result(wide_result(rows=200, cell_chars=200))
    assert "truncated" in text.lower() or "shortened" in text.lower()


def test_small_results_are_untouched() -> None:
    result = QueryResult(
        columns=("id", "name"), rows=((1, "a"), (2, "b")), elapsed_ms=3, truncated=False
    )
    text = format_query_result(result)
    assert "1 | a" in text and "2 | b" in text
    assert "(2 rows, 3 ms)" in text


def test_wide_cells_keep_the_beginning_of_each_value() -> None:
    # The head of a value is what identifies it; the tail is usually noise.
    result = QueryResult(
        columns=("t",), rows=(("IMPORTANT" + "z" * 5000,),), elapsed_ms=1, truncated=False
    )
    text = format_query_result(result)
    assert "IMPORTANT" in text
    assert len(text) <= 12_000
