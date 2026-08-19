# Evaluation

Two tracks (spec §三 v0.2.0), both runnable with one command:

1. **Self-built cases** (`cases.yaml`, 20 cases): measures what this project
   actually adds — metric-aware SQL, self-repair, clarify behaviour. Used for
   A/B runs with/without `metrics.yaml`.
2. **Public benchmark, split in two** (`public/`, ADR-004): a **dev** subset
   of 100 cases (seed 11) that failure analysis may use freely, and a
   **sealed test** subset of 200 cases (seed 2026). 198 questions are held
   in reserve, because exhausting the pool would be irreversible.

## Discipline (non-negotiable)

- **Never change the system in response to test results.** That is the rule;
  "run it once" was only ever a proxy for it. Re-running unchanged code
  under a different configuration leaks nothing; editing a prompt after
  seeing a test score does, however few times it is run. The dev subset
  exists so improvement work has a legitimate surface.
- Both samples are committed with their seeds, so anyone can reproduce the
  split and the numbers.
- **What the numbers support**: a before/after comparison on the same
  questions is paired and needs 57–114 cases; a cross-sample comparison
  (dev gain vs test gain) needs ~1089 per group to resolve 6pp and is out of
  reach here, so such comparisons are reported as directional only.
- Development iteration runs on DeepSeek (`--backend openai_compatible`);
  final report numbers additionally run one strong model. Both sets of
  numbers are published side by side.

## Five metrics

| metric | meaning |
|---|---|
| first-execution pass rate | result correct with zero failed SQL attempts |
| pass rate after self-repair | result correct after ≤3 retries |
| metric hit rate | expected metric names appear in the final answer |
| clarify-behaviour accuracy | asked when it should, didn't when it shouldn't |
| average tool calls | loop efficiency proxy |

Correctness = executed row sets compared as order-insensitive multisets with
float tolerance — never SQL text comparison (see
`queryagent/evals/compare.py` and ADR-003, pending).

## Running

```bash
# self-built cases against the demo SQLite db
queryagent eval --config examples/demo_ecommerce/config.sqlite.yaml --cases eval/cases.yaml

# dual-model: same cases, weak model via OpenAI-compatible endpoint
queryagent eval --config examples/demo_ecommerce/config.sqlite.yaml \
  --backend openai_compatible --model deepseek-chat --base-url https://api.deepseek.com

# public subset (after downloading databases, see public/README.md)
queryagent eval --config examples/demo_ecommerce/config.sqlite.yaml \
  --public eval/public/subset.json --db-dir eval/public/databases
```

`make eval` wraps the first command. Eval is deliberately **not** in CI — it
needs an LLM key and a database (spec §三).
