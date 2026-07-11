"""Public benchmark subset tooling — BIRD mini-dev / Spider dev (AI-OWNED).

Discipline (spec §三 v0.2.0, also in eval/README.md): the public subset is an
*external anchor*. Prompts and matching algorithms are never tuned against
it; it runs once per version acceptance. The sampling seed is fixed here and
the sampled subset JSON is committed to the repo, so the numbers are
reproducible by anyone.

Both benchmarks distribute questions as JSON plus per-question SQLite
databases, so cases run through the ordinary SQLiteConnector with zero extra
infrastructure. Downloads are manual (release URLs move); see
eval/public/README.md.

Usage:
    python -m queryagent.evals.public --source mini_dev_sqlite.json \\
        --out eval/public/subset.json --n 30
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Sequence
from pathlib import Path

from queryagent.evals.cases import EvalCase

SAMPLE_SEED = 42


def load_source_cases(path: str | Path) -> list[EvalCase]:
    """Load BIRD mini-dev or Spider dev questions (format auto-detected).

    BIRD items carry ``question_id``/``db_id``/``question``/``SQL``;
    Spider items carry ``db_id``/``question``/``query`` (id = list index).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of questions")
    cases: list[EvalCase] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: item {index} is not an object")
        db_id = str(item.get("db_id") or "")
        question = str(item.get("question") or "")
        sql = str(item.get("SQL") or item.get("query") or "")
        if not db_id or not question or not sql:
            raise ValueError(f"{path}: item {index} lacks db_id/question/SQL fields")
        question_id = item.get("question_id", index)
        cases.append(
            EvalCase(
                id=f"{db_id}_{question_id}",
                question=question,
                kind="public",
                expected_sql=sql,
                tags=("public",),
                db_id=db_id,
            )
        )
    return cases


def sample_cases(cases: Sequence[EvalCase], n: int, seed: int = SAMPLE_SEED) -> list[EvalCase]:
    """Deterministically sample ``n`` cases (sorted, seeded, then re-sorted)."""
    if n >= len(cases):
        return sorted(cases, key=lambda c: c.id)
    ordered = sorted(cases, key=lambda c: c.id)
    sampled = random.Random(seed).sample(ordered, n)
    return sorted(sampled, key=lambda c: c.id)


def write_subset(cases: Sequence[EvalCase], path: str | Path) -> None:
    """Write the sampled subset as committed-to-repo JSON."""
    payload = [
        {
            "id": case.id,
            "db_id": case.db_id,
            "question": case.question,
            "gold_sql": case.expected_sql,
        }
        for case in cases
    ]
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_subset(path: str | Path) -> list[EvalCase]:
    """Load a subset JSON produced by ``write_subset``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list")
    return [
        EvalCase(
            id=str(item["id"]),
            question=str(item["question"]),
            kind="public",
            expected_sql=str(item["gold_sql"]),
            tags=("public",),
            db_id=str(item["db_id"]),
        )
        for item in data
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Sample a public subset and report which databases it needs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="BIRD mini-dev or Spider dev JSON")
    parser.add_argument("--out", required=True, help="output subset JSON (commit this)")
    parser.add_argument("--n", type=int, default=30)
    args = parser.parse_args(argv)
    cases = load_source_cases(args.source)
    subset = sample_cases(cases, args.n)
    write_subset(subset, args.out)
    needed = sorted({case.db_id for case in subset})
    print(f"sampled {len(subset)}/{len(cases)} cases (seed={SAMPLE_SEED}) -> {args.out}")
    print(f"databases needed ({len(needed)}): {', '.join(needed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
