"""Regenerate the committed dev/test samples, exactly.

The two samples are not a plain "sample N with seed S": the test set
excludes every question whose results were ever observed, and the dev set
deliberately carries those retired questions (their known failures are
ready-made analysis material) topped up to size. Documenting that as a pair
of CLI commands got it wrong, so the derivation lives here as runnable code
and `tests/test_evals_public.py` asserts that it reproduces the committed
files byte for byte.

Usage:
    python eval/public/rebuild_samples.py --source path/to/mini_dev_sqlite.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from queryagent.evals.cases import EvalCase
from queryagent.evals.public import load_source_cases, sample_cases, write_subset

HERE = Path(__file__).parent
TEST_SEED = 2026
DEV_SEED = 11
TEST_SIZE = 200
DEV_SIZE = 100


def build(source: str | Path) -> tuple[list[EvalCase], list[EvalCase]]:
    """Return (test, dev) exactly as committed.

    Args:
        source: BIRD mini-dev question JSON.

    Returns:
        The sealed test sample and the dev sample, disjoint by construction.
    """
    pool = load_source_cases(source)
    retired = set(json.loads((HERE / "retired-ids.json").read_text(encoding="utf-8")))
    test = sample_cases(pool, TEST_SIZE, seed=TEST_SEED, exclude=retired)
    test_ids = {c.id for c in test}
    carried = [c for c in pool if c.id in retired]
    topup = sample_cases(
        pool, DEV_SIZE - len(carried), seed=DEV_SEED, exclude=test_ids | retired
    )
    dev = sorted(carried + topup, key=lambda c: c.id)
    return test, dev


def main() -> int:
    """Rewrite subset.json and dev-subset.json from the source questions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    test, dev = build(args.source)
    write_subset(test, HERE / "subset.json")
    write_subset(dev, HERE / "dev-subset.json")
    print(f"test {len(test)} · dev {len(dev)} · 两者不相交")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
