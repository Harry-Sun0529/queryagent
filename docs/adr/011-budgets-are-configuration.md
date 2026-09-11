# ADR-011: Budgets are configuration, admitted before anything runs

Status: accepted · Date: 2026-09-11

## Decision

Totals across statements are set in one place, the optional `budget:`
section of `config.yaml`:

- statements per request (a confirmed run with its freshness probe, or one
  agent question);
- statements, and client-measured seconds, per subject per business day
  (`workflow.timezone`);
- requests executing at once against one state file;
- on ClickHouse only, rows one statement may read (`max_rows_to_read`,
  enforced by the engine).

No command-line flag, workflow rule, document or tool argument reaches them.
A `SqliteBudgetLedger` in the workflow state file admits each request before
its first statement; concurrency is a lease with an expiry. `flow` admits
after every check that needs no database and before the idempotency claim.
The agent path (`ask`, `chat`) admits each statement, and a refusal comes
back to the model as an error observation. `eval` is not metered: it is a
maintainer measuring, not someone using the data.

Absent section, no totals — the behaviour of every release before 0.9.

## Context

The handoff asked for totals "configured by a maintainer, which neither the
model nor the user can raise", and noted that a row cap is not a scan limit.
SECURITY.md had said since v0.5 that per-source budgets and admission
control did not exist. v1.0 lets other agents call this code; an unbounded
caller is a real cost, not a theoretical one.

## Consequences

- (+) A refused request touches the database zero times, and in `flow`
  leaves its idempotency key unspent.
- (+) One ledger for both paths; the agent path and the confirmed path
  cannot drift apart on what a statement costs.
- (+) A limit that cannot be enforced is refused when the file loads: an
  unknown key, or a scan limit on MySQL or SQLite. A limit written down but
  not applied would be a false statement about the deployment.
- (−) Seconds are measured by the client and include the network. They are
  checked before a statement, so the last statement of a day can overshoot
  by up to one `safety.timeout_s`.
- (−) MySQL and SQLite have no scan limit; the per-statement timeout is the
  only bound there.
- (−) An allowance is per subject id, so it is only as strong as the
  identity. Locally, `flow --subject` is the trusted user's own choice; a
  deployment that needs per-person allowances needs the identity to come
  from a host (MCP, Web — v1.0). `max_concurrent` is per state file and not
  affected.
- (−) One state file; replicas do not share a ledger (the 1A boundary).
