"""The ReAct agent loop — the core of QueryAgent.

Framework-free by design: the whole control flow is this one generator, so
every decision (when to stop, when to retry, when to ask the user) is
readable and single-step debuggable.

The loop yields ``AgentEvent`` objects and never renders anything; the CLI,
the eval runner and any future UI are just different consumers of the same
stream (spec §二).

Termination is always explicit — one of five events ends the stream:

1. ``AnswerEvent`` — the model answered without requesting a tool;
2. ``ErrorEvent("MaxTurns")`` — turn budget exhausted (default 8);
3. ``ErrorEvent("RepeatedAction")`` — the model proposed the exact same
   tool call (name + arguments) twice in a row: dead-loop protection;
4. ``ErrorEvent("SafetyViolation")`` — the safety layer rejected a
   statement; deliberately terminal rather than retryable, because a model
   that just tried to write should not get more attempts this run;
5. ``ClarifyEvent`` — the model invoked the clarification tool because
   matched metric definitions conflict; the caller collects the user's
   reply and starts a new run with it.

Failure handling inside a run:
- Model output that cannot be used (``LLMParseError`` or an empty response)
  is retried once with the error fed back; on the second failure the loop
  degrades to a plain no-tools completion (spec §三 v0.1.0).
- Failed tool calls (bad SQL, bad arguments) come back as error
  observations the model can read and fix — each one emits a
  ``RetryEvent``; after ``max_retries`` failures the loop gives up with an
  explanation instead of burning the remaining turns (spec §三 v0.1.1).
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator, Sequence

from queryagent.context import ContextBuilder
from queryagent.errors import LLMParseError, SafetyViolation
from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    RetryEvent,
    ThinkEvent,
    ToolCallEvent,
    UsageEvent,
)
from queryagent.llm.base import LLMBackend, Message, ModelResponse, ToolCall
from queryagent.tools import CLARIFY_TOOL_NAME, ToolRegistry


def run_agent(
    question: str,
    *,
    backend: LLMBackend,
    registry: ToolRegistry,
    context_builder: ContextBuilder,
    max_turns: int = 8,
    max_retries: int = 3,
    conversation: Sequence[Message] = (),
) -> Iterator[AgentEvent]:
    """Run the ReAct loop for one question, yielding AgentEvents.

    Args:
        question: The user's natural-language question.
        backend: LLM provider (Anthropic / OpenAI-compatible / test fake).
        registry: Validated tool dispatch (get_schema / execute_sql / ...).
        context_builder: Assembles per-turn message lists (schema, metrics,
            history, budget trimming).
        max_turns: Hard cap on model calls in the tool loop.
        max_retries: Failed tool observations tolerated before giving up.
        conversation: Finished prior turns of a chat session (plain
            user/assistant text messages), so follow-up questions can refer
            back to earlier answers. Empty for one-shot runs and eval.

    Yields:
        AgentEvent instances; the stream always ends with one of the five
        explicit terminal events documented in the module docstring.
    """
    history: list[Message] = []
    last_action: tuple[str, str] | None = None
    parse_failures = 0
    failed_observations = 0

    for _ in range(max_turns):
        started = time.monotonic()
        try:
            response = backend.complete(
                context_builder.build(question, history, conversation=conversation),
                tools=registry.specs(),
            )
        except LLMParseError as exc:
            parse_failures += 1
            yield RetryEvent(reason=f"model output unusable: {exc}", attempt=parse_failures)
            if parse_failures <= 1:
                history.append(_parse_failure_notice(str(exc)))
                continue
            yield from _degraded_answer(
                question,
                backend=backend,
                context_builder=context_builder,
                history=history,
                conversation=conversation,
            )
            return

        usage_event = _usage_event(response, started)
        if usage_event is not None:
            yield usage_event

        if not response.tool_calls:
            text = response.text.strip()
            if not text:  # empty response: same treatment as a parse failure
                parse_failures += 1
                yield RetryEvent(reason="model returned an empty response", attempt=parse_failures)
                if parse_failures <= 1:
                    history.append(_parse_failure_notice("your reply was empty"))
                    continue
                yield from _degraded_answer(
                    question,
                    backend=backend,
                    context_builder=context_builder,
                    history=history,
                    conversation=conversation,
                )
                return
            yield AnswerEvent(text=text)
            return

        if response.text.strip():
            yield ThinkEvent(text=response.text.strip())

        # One action per turn: with multiple proposed calls the observations
        # would interleave confusingly in history, so extras are dropped and
        # the model re-proposes them next turn if it still wants them.
        call = response.tool_calls[0]

        if call.name == CLARIFY_TOOL_NAME:
            yield _to_clarify_event(call)
            return

        action = (call.name, json.dumps(call.arguments, sort_keys=True, ensure_ascii=False))
        if action == last_action:
            yield ErrorEvent(
                error_type="RepeatedAction",
                message=f"identical '{call.name}' call proposed twice in a row; stopping",
            )
            return
        last_action = action

        yield ToolCallEvent(tool_name=call.name, arguments=call.arguments, tool_call_id=call.id)
        try:
            observation = registry.validate_and_dispatch(call.name, call.arguments)
        except SafetyViolation as exc:
            yield ErrorEvent(error_type="SafetyViolation", message=str(exc))
            return
        yield ObservationEvent(
            content=observation.content, is_error=observation.is_error, tool_call_id=call.id
        )

        if observation.is_error:
            failed_observations += 1
            yield RetryEvent(
                reason=_first_line(observation.content), attempt=failed_observations
            )
            if failed_observations > max_retries:
                yield ErrorEvent(
                    error_type="RetryLimit",
                    message=(
                        f"giving up after {failed_observations} failed tool calls; "
                        f"last error: {_first_line(observation.content)}"
                    ),
                )
                return

        history.append(
            Message(
                role="assistant",
                content=response.text,
                tool_calls=(call,),
                reasoning=response.reasoning,
            )
        )
        history.append(
            Message(role="tool", content=observation.content, tool_call_id=call.id)
        )

    yield ErrorEvent(
        error_type="MaxTurns",
        message=f"no final answer after {max_turns} turns",
    )


def _degraded_answer(
    question: str,
    *,
    backend: LLMBackend,
    context_builder: ContextBuilder,
    history: list[Message],
    conversation: Sequence[Message] = (),
) -> Iterator[AgentEvent]:
    """Last resort after repeated parse failures: plain completion, no tools."""
    started = time.monotonic()
    try:
        response: ModelResponse = backend.complete(
            context_builder.build(question, history, conversation=conversation)
        )
    except Exception as exc:  # noqa: BLE001 - deliberate: report, never crash the stream
        yield ErrorEvent(error_type="LLMParseError", message=str(exc))
        return
    usage_event = _usage_event(response, started)
    if usage_event is not None:
        yield usage_event
    text = response.text.strip()
    if text:
        yield AnswerEvent(text=text)
    else:
        yield ErrorEvent(error_type="LLMParseError", message="model produced no usable output")


def _usage_event(response: ModelResponse, started: float) -> UsageEvent | None:
    """Pair the provider's token counts with the latency the user actually felt.

    Latency is measured around the whole call, so backend-level retries show
    up as the wait they really were.
    """
    if response.usage is None:
        return None
    return UsageEvent(
        model=response.usage.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cached_input_tokens=response.usage.cached_input_tokens,
        latency_ms=int((time.monotonic() - started) * 1000),
    )


def _parse_failure_notice(detail: str) -> Message:
    return Message(
        role="user",
        content=(
            f"(system notice) Your previous reply could not be used: {detail}. "
            "Reply again — either call a tool or give the final answer as text."
        ),
    )


def _to_clarify_event(call: ToolCall) -> ClarifyEvent:
    """Convert an ask_clarification tool call into the terminal ClarifyEvent."""
    raw_metrics = call.arguments.get("metrics", [])
    metrics = tuple(str(m) for m in raw_metrics) if isinstance(raw_metrics, list) else ()
    question_text = str(call.arguments.get("question") or "").strip()
    if not question_text:
        question_text = "这个问题涉及多种业务口径，请说明你要用哪一种。"
    return ClarifyEvent(question=question_text, conflicting_metrics=metrics)


def _first_line(text: str) -> str:
    return text.splitlines()[0] if text else ""
