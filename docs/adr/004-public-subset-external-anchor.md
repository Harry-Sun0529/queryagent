# ADR-004: Public benchmark subset as an external anchor (dev/test split)

Status: accepted · Date: 2026-08-19 (supersedes the 2026-08-17 version)

## Decision

BIRD mini-dev is split into two fixed-seed samples, both committed:

- **test set** — 30 cases, seed 42 (`eval/public/subset.json`). Sealed:
  never analysed, never tuned against, run only at version acceptance.
- **dev set** — 30 cases, seed 7, sampled with the test-set ids excluded
  (`eval/public/dev-subset.json`). Free to analyse and iterate against.

The gap between dev and test improvement is reported as the overfitting
measurement.

## Context

The earlier version of this ADR said simply "never look at the public
subset". That protects the anchor but makes the project unable to answer
"how would you improve these numbers?" — the honest answer became "I don't
know, I'm not allowed to look", which is a worse position than having a
disciplined way to look.

A train/dev/test split is the standard resolution and is *more* defensible
than abstinence: it permits systematic improvement while keeping an unfitted
reference. `sample_cases(..., exclude=)` makes disjointness a tested
property, not a promise.

## Consequences

- (+) Failure analysis has a legitimate surface; improvements are evidence-
  driven instead of guesses.
- (+) The dev/test delta quantifies generalisation — a number that "we never
  looked" can never produce.
- (+) Anyone can reproduce both samples from the repo (seeds + exclude list
  are committed).
- (−) Two eval runs per acceptance instead of one.
- (−) Dev and test share databases, so schema familiarity is not isolated.
  Accepted: no tuning targets schemas, and question-level disjointness is
  what the claim rests on.
