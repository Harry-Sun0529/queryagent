# ADR-005: Traces on by default, with a hard privacy backstop

Status: accepted · Date: 2026-08-19

## Decision

`chat` and `ask` record the full event stream to `.queryagent/traces/*.jsonl`
by default — question, SQL, observations and token usage. Three mitigations
ship with it:

1. a one-time stderr notice on first write, naming the directory, what it
   contains and how to switch it off;
2. `--no-trace` and config `trace: false`;
3. `.queryagent/` in `.gitignore`.

## Context

A non-deterministic agent cannot be debugged from a terminal scrollback that
is already gone. The alternative designs were: off by default (safer, but
the trace is missing exactly when something went wrong the first time), or
on-but-redacted, recording SQL and events without result rows.

Redaction was tempting — result rows are rarely what you need to reconstruct
a failure. It was rejected as the default because a partially recorded trace
invites false confidence: the one time the bug *is* in the data (a NULL, an
encoding, an unexpected row count), a redacted trace sends you looking in
the wrong place.

## Consequences

- (+) Every run is reconstructible via `queryagent replay`.
- (+) The gitignore entry protects against the realistic failure mode —
  someone pointing the agent at a production database inside a repo and
  committing everything — which a documentation note would not.
- (−) Business data lands on local disk by default. Documented in
  SECURITY.md and announced at runtime; users on sensitive data should set
  `trace: false`.
- Retention is capped at the 50 most recent traces so the directory cannot
  grow without bound.
