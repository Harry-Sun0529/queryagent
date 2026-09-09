# ADR-004: Public benchmark as an external anchor (dev/test split)

Status: accepted · Date: 2026-08-19 (supersedes the two earlier versions)

## Decision

BIRD mini-dev is split into two committed, fixed-seed samples:

- **test** — 200 cases, seed 2026 (`eval/public/subset.json`). Sealed.
- **dev** — 100 cases, seed 11 (`eval/public/dev-subset.json`). Free to
  analyse and iterate against.

198 questions are deliberately held in reserve.

The governing rule is **"never change the system in response to test
results"** — not "run test only once". The earlier wording confused the
mechanism with the purpose: what must be prevented is information flowing
from test outcomes back into prompts, matching or code. Re-running the same
unchanged system under a different configuration leaks nothing; changing a
prompt after seeing a test score does, however few times it is run.

## Context

The sample sizes are an engineering budget, not a universal power guarantee.
Paired before/after comparisons depend on the target effect and the frequency
of discordant outcomes. The earlier “57–114” and “1089 per group” claims lacked
sufficient assumptions and are withdrawn as general guidance. Prespecify an
experiment and its uncertainty analysis before interpreting a difference.

The reserve exists because exhausting the pool is irreversible: if the test
set is ever compromised, a clean replacement can only come from questions
that were never used.

The previous test sample is retired into dev. It was never tuned against,
but its per-case pass/fail table was inspected during two acceptances, and
the whole claim rests on results never having been examined case by case.

## Consequences

- (+) The larger sample supports more informative measurements; adequacy of
  power still depends on a specified comparison.
- (+) The rule now states its purpose, so it survives questions like "is a
  second configuration run cheating?" (it is not) without ad-hoc exceptions.
- (+) Retired questions carry known failures into dev, where they are useful
  as ready-made failure-analysis material.
- (−) A test run costs ~45 minutes; eval checkpointing exists so that cost
  is not lost to a mid-run failure.
- (−) Numbers measured on the retired 30-case samples are not comparable to
  the current ones. Historical CHANGELOG entries keep their original values
  and say so; the README carries current numbers only.
