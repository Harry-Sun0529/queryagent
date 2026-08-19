# Evaluation

Two tracks (spec §三 v0.2.0), both runnable with one command:

1. **Self-built cases** (`cases.yaml`, 20 cases): measures what this project
   actually adds — metric-aware SQL, self-repair, clarify behaviour. Used for
   A/B runs with/without `metrics.yaml`.
2. **Public benchmark, split in two** (`public/`, ADR-004): a **dev** subset
   (seed 7) that failure analysis may use freely, and a **sealed test**
   subset (seed 42) that runs once per release and is never analysed. The
   gap between dev and test improvement is the overfitting measurement.

## Discipline (non-negotiable)

- Prompts and matching algorithms are **never tuned against the test
  subset** (seed 42). It runs once per version acceptance and the README
  reports it as-is, including failures. The dev subset (seed 7) exists
  precisely so improvement work has a legitimate surface.
- The sampling seed is fixed (`SAMPLE_SEED = 42` in
  `queryagent/evals/public.py`) and the sampled `subset.json` is committed,
  so anyone can reproduce both the subset and the numbers.
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
