# ADR-010: Before confirmation, no business query — and at most a freshness probe

Status: accepted · Date: 2026-09-11 · Narrows invariant I2 of slice 1A

## Decision

I2 said "no query runs before a confirmation". It now reads: **no business
query runs before a confirmation.** The sheet may say how far the data
reaches in one of two ways, chosen by the maintainer with
`workflow.freshness_before_confirm`:

- `declared` (the default): each structured mapping may declare its update
  cadence, `freshness: {lag_days: N}` (T+N). From today's business date the
  sheet works out what should be there and says when the period runs past
  it. No statement runs — I2 in its original form still holds.
- `probe`: the compiler's own `SELECT MAX(time_column) FROM table` may run
  before confirmation — generated from identifiers validated when the
  mappings load, never from the question or a document — with its own short
  timeout (`freshness_probe_timeout_s`), cached per table
  (`freshness_cache_minutes`) and charged to the budget like any other
  statement (ADR-011).
- `off`: nothing is said before the result.

Whatever the sheet says is advice. It is not stored on the draft and not in
its content hash. The confirmed run still probes at execution time, and the
result reports that answer. A run records what the declared cadence expected
(`expected_through`), and when the data is older than that, the result says
by how many days.

## Context

v0.8 wrote down the cost of the old rule: a partial month could be named only
on the result, after the user had approved a 口径 whose number would cover
22 days under a 31-day heading. Knowing takes a query, and I2 forbade it. The
alternatives were to keep the cost, to break the rule wholesale, or to name
exactly which statement may run and under what limits. This ADR takes the
third.

## Consequences

- (+) The default deployment runs nothing before confirmation, as before.
  Relaxing it is a maintainer's written choice.
- (+) Before confirmation, only one shape of statement can run. The tests
  count statements and compare each one to the compiler's probe.
- (+) A declared cadence doubles as a load monitor: a table further behind
  than its maintainer said it would be is named on the result.
- (−) A probe's answer can be stale by up to `freshness_cache_minutes`, and
  the data can load between the sheet and the run. That is why the note is
  advice, stamped with its time, and why the result re-probes.
- (−) A declared cadence is a promise, not a fact: a wrong declaration gives
  a wrong warning on the sheet. The lag note on the result is where a wrong
  declaration shows.
- (−) A probe reveals one fact — the newest record's date in a mapped table
  — to anyone who can prepare a draft, before they confirm. Anyone who can
  run the mapped query already learns it; the cache is not scoped by
  subject for the same reason.
