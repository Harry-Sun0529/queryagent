"""ReAct agent loop. **HUMAN-OWNED — spec §〇, Claude Code must not implement.**

What belongs here (spec §三 v0.1.0):

* The ReAct loop driving ``LLMBackend.complete`` +
  ``ToolRegistry.validate_and_dispatch``.
* Four explicit termination conditions:
    1. the model produces a final answer;
    2. turn count reaches ``max_turns`` (default 8);
    3. the same action (tool + arguments) repeats twice in a row
       (dead-loop protection);
    4. a ``SafetyViolation`` escapes the tool layer.
* Parse-failure handling: retry once with the error fed back, then degrade to
  a direct answer.
* Later versions (leave seams, don't build yet): v0.1.1 self-correction
  (``QueryError`` observations fed back, max 3 retries, ``RetryEvent``);
  v0.2.0 clarify triggering (``ClarifyEvent`` on metric caution conflicts).

The loop yields ``AgentEvent`` objects (queryagent/events.py) and never
prints or renders — every consumer reads the event stream.
``tests/test_agent_termination.py`` encodes the acceptance criteria; remove
its skip marker once this is implemented.
"""

from __future__ import annotations

from collections.abc import Iterator

from queryagent.context import ContextBuilder
from queryagent.events import AgentEvent
from queryagent.llm.base import LLMBackend
from queryagent.tools import ToolRegistry


def run_agent(
    question: str,
    *,
    backend: LLMBackend,
    registry: ToolRegistry,
    context_builder: ContextBuilder,
    max_turns: int = 8,
) -> Iterator[AgentEvent]:
    """Run the ReAct loop for one question, yielding AgentEvents.

    HUMAN-OWNED: implementation intentionally left to the human author
    (spec §〇 — this file is the project's interview-defensible core).
    """
    raise NotImplementedError(
        "queryagent/agent.py is HUMAN-OWNED (spec §〇): implement the ReAct loop here"
    )
