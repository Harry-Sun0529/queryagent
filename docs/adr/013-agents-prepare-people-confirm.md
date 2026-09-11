# ADR-013: Agents prepare and execute over MCP; only people confirm

Status: accepted · Date: 2026-09-11

## Decision

`queryagent mcp` serves the confirmation-gated flow to an agent host (Claude
Code, Claude Desktop) over stdio MCP. It is one more adapter over
`QueryWorkflow`, assembled by the same `workflow/wiring.py` as the terminal,
and it has five tools: `list_metrics`, `prepare_query`, `amend_query`,
`query_status`, `execute_query`. **There is no tool that confirms.**

- **Identity comes from the command that starts the server**
  (`--subject`, `--workspace`, written into the host's configuration). No
  tool takes a subject or a workspace; an argument no tool takes is refused.
- **Every door has a channel** (`cli`, `web`, `mcp`), set by the door on the
  trusted `ActorContext`. The channel decides a rule's provenance: a person's
  amendment is 「本次约定」 (`RuleSource.USER`), an agent's is 「Agent 代填」
  (`RuleSource.AGENT`). The service refuses a rule claiming any other source.
- **`confirm()` refuses the MCP channel**, before it reads anything. The tool
  table already offers no way to reach it; this is the second wall.
- **A confirmation records its channel.** No code writes `mcp`, and the read
  that `execute_query` relies on accepts only `cli` and `web`.
- **`execute_query` names a draft**, not a confirmation
  (`QueryWorkflow.execute_confirmed`). The service looks up a confirmation a
  person gave the draft's current version and hash; without one, nothing
  runs. The confirmation is the idempotency key: one confirmation authorises
  one run, asking again returns that run, and running again takes a person
  confirming again.
- The protocol is written by hand: JSON-RPC 2.0, one message per line,
  revision `2025-06-18`, methods `initialize`, `ping`, `tools/list`,
  `tools/call`. stdout carries frames only; everything for a person goes to
  stderr.

A person confirms in the terminal (`queryagent confirm`) or on the local
confirmation page (`queryagent web`, T45).

## Context

The product's value is the confirmation gate. An agent inside a host can
already do anything a tool lets it do, including "clicking confirm" on its
user's behalf, and a gate the agent is merely asked to respect is not a gate.
Making confirmation *unexpressible* over MCP is the only version of the rule
that does not depend on the agent's behaviour.

The plan asked for an agent-supplied idempotency key. It was dropped: with
one, an agent can run a confirmed draft as often as it likes by changing the
key, and "a person approved this" would stretch to cover runs nobody
approved.

## Consequences

- (+) "Can the agent confirm for me?" has a structural answer: there is no
  tool, and the service would refuse one.
- (+) What an agent guessed stays visibly the agent's, on the sheet and on
  the result (「X 由 Agent 代填、经你确认」), and is part of the hash.
- (+) The MCP door gets every check the terminal has: evidence re-checks,
  budgets, freshness, history, because it is the same assembly.
- (−) **Honest boundary:** an agent with an arbitrary shell as the same OS
  user can run `queryagent confirm`, or write to the state file. This design
  stops confirmation through the tool protocol and from other websites (T45),
  not an agent that has taken over the machine. Multi-user deployments need
  real authentication, which 1.0 does not provide.
- (−) `RuleSource.AGENT` is a one-way change: v0.9 cannot open a draft that
  contains it, and v0.9 cannot write a confirmation into a state file that
  has the `channel` column. State files written by v0.9 open in 1.0.
- (−) A failed run consumes its confirmation. Retrying takes a person
  confirming again, which is deliberate and occasionally tedious.
- (−) History does not remember what an agent filled in: 「历史选择」 says
  "your choice", and an agent's guess that a person approved is not quite
  that.
