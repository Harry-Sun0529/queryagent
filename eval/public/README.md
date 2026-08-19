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
3. Reproduce the committed samples:

   ```bash
   python eval/public/rebuild_samples.py --source path/to/mini_dev_sqlite.json
   ```

   The derivation is not a plain "sample N with seed S" — the test set
   excludes every question whose results were ever observed
   (`retired-ids.json`), and the dev set deliberately carries those retired
   questions topped up to size. That is why it lives in a script rather
   than in a command line here: `tests/test_evals_public.py` asserts the
   script reproduces the committed files exactly.

   Exact duplicates in the upstream file are collapsed (mini-dev ships two
   questions twice), so the pool is 498 rather than 500. The databases the
   samples need go in `eval/public/databases/` (gitignored — they are large).

4. Run: see `eval/README.md`.

## Discipline

`subset.json` and `dev-subset.json` are committed; `databases/` is not.

The rule is **never change the system in response to test results** — not
"run it once", which was only ever a proxy for it. Re-running unchanged code
under a different configuration leaks nothing; editing a prompt after seeing
a test score does, however few times it is run. The dev subset exists so
that improvement work has a legitimate surface (ADR-004).
