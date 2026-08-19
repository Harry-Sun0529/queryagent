# ADR-001: No agent framework

Status: accepted · Date: 2026-08-19

## Decision

The ReAct loop, tool dispatch, context assembly and event stream are written
by hand (~200 lines in `agent.py`); no LangChain/LlamaIndex/agent SDK.

## Context

Frameworks buy speed at the cost of opacity: retry policy, termination
conditions and prompt assembly live behind someone else's abstractions. This
project's core value is that every control-flow decision is visible,
single-step debuggable, and defensible line by line.

## Consequences

- (+) The whole loop is one generator; termination is provably explicit
  (five terminal events, each with a test).
- (+) Zero framework dependencies to track CVEs or breaking releases for.
- (−) Features frameworks give for free (streaming, parallel tool calls)
  must be built when actually needed — see the one-action-per-turn note in
  `agent.py`.
