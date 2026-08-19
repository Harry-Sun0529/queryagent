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

Sizing follows from which comparison is being made, and the two are not the
same test:

| comparison | design | cases needed (80% power) |
|---|---|---|
| before/after on the same questions | paired (McNemar) | 57–114 |
| gain on dev vs gain on test | independent samples | ~1089 per group for 6pp |

At the previous size of 30, even the paired comparison was underpowered.
200 comfortably covers release-over-release comparisons on the sealed set;
the cross-sample question is out of reach at any size this project can
afford (2178 questions would require mixing in Spider, whose gold-SQL
conventions differ enough to introduce their own bias).

The reserve exists because exhausting the pool is irreversible: if the test
set is ever compromised, a clean replacement can only come from questions
that were never used.

The previous test sample is retired into dev. It was never tuned against,
but its per-case pass/fail table was inspected during two acceptances, and
the whole claim rests on results never having been examined case by case.

## Consequences

- (+) Paired release-over-release comparisons are adequately powered.
- (+) The rule now states its purpose, so it survives questions like "is a
  second configuration run cheating?" (it is not) without ad-hoc exceptions.
- (+) Retired questions carry known failures into dev, where they are useful
  as ready-made failure-analysis material.
- (−) A test run costs ~45 minutes; eval checkpointing exists so that cost
  is not lost to a mid-run failure.
- (−) Numbers measured on the retired 30-case samples are not comparable to
  the current ones. Historical CHANGELOG entries keep their original values
  and say so; the README carries current numbers only.
