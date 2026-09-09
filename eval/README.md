# Evaluation

Two tracks (spec §三 v0.2.0), both runnable with one command:

1. **Self-built cases** (`cases.yaml`, 36 cases): measures what this project
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
- **What the numbers support**: paired comparisons require an explicit
  target effect, discordant-outcome assumptions and power calculation. Sample
  size alone does not establish significance or equivalence. New sample final
  scores cannot explain old sample gains.
- Development iteration runs on DeepSeek (`--backend openai_compatible`);
  final report numbers additionally run one strong model. Both sets of
  numbers are published side by side.

## Scoring v2

| metric | meaning |
|---|---|
| first-execution pass rate | the first SQL itself returned the complete expected row set; later errors do not change this |
| query-trajectory hit rate | any successfully executed SQL reproduced the complete expected row set |
| completed with SQL hit | a trajectory hit AND a nonempty normal answer, with no terminal error or clarification |
| metric hit rate | expected metric names appear in the final answer; not proof the SQL used that definition |
| clarify-behaviour accuracy | asked when it should, did not when it should not |
| average tool calls | loop efficiency proxy |

**Natural-language answer correctness is not measured.** An answer can be
wrong even when a SQL query was correct. “Completed with SQL hit” measures
completion, not semantic correctness; the next structured-answer workflow
needs a separate acceptance test. Error-terminated runs cannot qualify for
completion or a successful eval exit code. Legacy logs without completion
metadata report that measurement as unavailable.

Row-set matching uses order-insensitive multisets and float tolerance.
Truncated results cannot establish equality of the full answer. Historical
v0.5.0 reports keep their numbers and legacy names; their “after self-repair”
rate was trajectory matching, not final-answer accuracy. First-execution
semantics changed in v2, so old and new first-pass rates are not comparable.

## Resume and concurrency

Each completed case is flushed to the JSONL checkpoint, independently of
report order. A partial/corrupt line costs only that line. This protects
against process termination, not storage failure or loss of unflushed kernel
buffers during power loss.

`--resume` checks case contents, effective model and safety settings, metrics,
local SQLite snapshots (including WAL), current date and implementation files.
Old or missing signatures cannot be resumed. Trace paths and concurrency do
not define the experiment. Keep input databases immutable during a run;
remote model versions can still change outside our control.

For a server database, supply `--data-version <immutable-snapshot-id>` from
the initial run; it is required for resume. QueryAgent does not scan a remote
database to invent a snapshot ID, and the operator must keep that snapshot
unchanged. Secrets are excluded from stored identity.

Parallel eval has at most N cases in flight. Five consecutive unmeasured
completions stop further submissions; already in-flight cases finish and
measured results are saved. The streak follows completion order, unlike the
legacy submission-order implementation. Reports remain in case order.

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
