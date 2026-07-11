"""Acceptance tests for the four agent termination paths (spec §三 v0.1.0).

The agent loop is HUMAN-OWNED; these tests pin the *contract* (the loop
terminates, and how it signals why) while leaving the internal design free.
Remove the module-level skip once queryagent/agent.py is implemented.
"""

from __future__ import annotations

import pytest

from queryagent.agent import run_agent
from queryagent.context import ContextBuilder
from queryagent.errors import SafetyViolation
from queryagent.events import AnswerEvent, ErrorEvent, ToolCallEvent
from queryagent.tools import ToolRegistry, ToolSpec
from tests.fakes import FakeLLMBackend, answer, tool_call

pytestmark = pytest.mark.skip(
    reason="agent.py is HUMAN-OWNED and not implemented yet; remove once run_agent lands"
)


def make_registry(handler=None) -> ToolRegistry:
    return ToolRegistry(
        [
            ToolSpec(
                name="echo",
                description="Echo a message back.",
                input_schema={
                    "type": "object",
                    "properties": {"msg": {"type": "string"}},
                    "required": ["msg"],
                },
                handler=handler or (lambda msg: f"echo: {msg}"),
            )
        ]
    )


def make_builder() -> ContextBuilder:
    return ContextBuilder(schema_text="TABLE t\n  id INT NOT NULL", dialect="mysql")


def test_terminates_on_final_answer() -> None:
    backend = FakeLLMBackend([answer("42")])
    events = list(
        run_agent(
            "meaning of life",
            backend=backend,
            registry=make_registry(),
            context_builder=make_builder(),
        )
    )
    assert isinstance(events[-1], AnswerEvent)
    assert events[-1].text == "42"


def test_terminates_on_max_turns() -> None:
    # Distinct arguments each turn so dead-loop protection does not fire first.
    script = [tool_call("echo", {"msg": f"m{i}"}, call_id=f"c{i}") for i in range(20)]
    backend = FakeLLMBackend(script)
    events = list(
        run_agent(
            "loop forever",
            backend=backend,
            registry=make_registry(),
            context_builder=make_builder(),
            max_turns=3,
        )
    )
    tool_events = [e for e in events if isinstance(e, ToolCallEvent)]
    assert len(tool_events) <= 3
    # How the limit is reported (ErrorEvent vs degraded AnswerEvent) is the
    # human's design; the contract is only that the stream ends explicitly.
    assert isinstance(events[-1], (AnswerEvent, ErrorEvent))


def test_terminates_on_repeated_action() -> None:
    # Same tool with identical arguments every turn: dead-loop protection
    # must stop the loop before max_turns is exhausted.
    script = [tool_call("echo", {"msg": "same"}, call_id=f"c{i}") for i in range(10)]
    backend = FakeLLMBackend(script)
    events = list(
        run_agent(
            "repeat yourself",
            backend=backend,
            registry=make_registry(),
            context_builder=make_builder(),
            max_turns=8,
        )
    )
    tool_events = [e for e in events if isinstance(e, ToolCallEvent)]
    assert len(tool_events) < 8
    assert isinstance(events[-1], (AnswerEvent, ErrorEvent))


def test_terminates_on_safety_violation() -> None:
    def blocked_handler(msg: str) -> str:
        raise SafetyViolation("blocked by safety layer", sql=msg)

    backend = FakeLLMBackend([tool_call("echo", {"msg": "DROP TABLE users"})])
    events = list(
        run_agent(
            "do something unsafe",
            backend=backend,
            registry=make_registry(blocked_handler),
            context_builder=make_builder(),
        )
    )
    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].error_type == "SafetyViolation"
