# ADR-004: Public benchmark subset as an external anchor

Status: accepted · Date: 2026-08-19

## Decision

Besides the 20 self-built cases, a fixed-seed (42) 30-case sample of BIRD
mini-dev runs at each version acceptance — exactly once, and prompts or
matching are never tuned against it. The sampled `subset.json` is committed.

## Context

Self-built numbers invite the "you graded your own homework" objection —
legitimately: the self-built set exists to be iterated on (it measures the
metric/clarify features and drives fixes, as its git history shows). The
anchor's job is to show what those iterations did *not* overfit.

## Consequences

- (+) Anyone can reproduce both the sample (seed committed) and the run.
- (+) The self-built vs anchor gap is itself informative (schema
  unfamiliarity shows up as more exploration tool-calls).
- (−) Anchor numbers lag model/prompt improvements by design; they only
  move at acceptance runs.
