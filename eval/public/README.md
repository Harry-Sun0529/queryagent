# Public benchmark subset (external anchor)

Source: **BIRD mini-dev** (preferred; ~500 questions with SQLite databases)
or Spider dev. Both ship questions as JSON + per-question SQLite databases,
so cases run through the ordinary sqlite connector — zero extra
infrastructure (spec §三 v0.2.0).

## Prepare (manual download — release URLs move)

1. Download BIRD mini-dev from https://github.com/bird-bench/mini_dev
   (or Spider dev from https://yale-lily.github.io/spider).
2. Unpack so you have the question JSON and a `databases/` directory laid out
   as `databases/<db_id>/<db_id>.sqlite`.
3. Sample the fixed subset (seed 42, committed to the repo):

   ```bash
   python -m queryagent.evals.public \
       --source path/to/mini_dev_sqlite.json \
       --out eval/public/subset.json --n 30
   ```

   The command prints which `db_id` databases the subset needs; copy those
   into `eval/public/databases/` (gitignored — databases are large).

4. Run: see `eval/README.md`.

## Discipline

`subset.json` is committed; `databases/` is not. Prompts and matching are
never tuned against this subset (spec §三) — it exists precisely so the
self-built numbers have an unfitted external reference. HUMAN samples are
spot-checked after sampling (spec §〇: AI-OWNED script + HUMAN 抽样确认).
