"""Unit tests for public-benchmark subset tooling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from queryagent.evals.public import (
    load_source_cases,
    load_subset,
    sample_cases,
    write_subset,
)

BIRD_ITEMS = [
    {"question_id": i, "db_id": f"db{i % 3}", "question": f"q{i}", "SQL": f"SELECT {i}"}
    for i in range(20)
]
SPIDER_ITEMS = [
    {"db_id": "concert", "question": "how many singers", "query": "SELECT count(*) FROM singer"}
]


def write_json(tmp_path: Path, name: str, data: object) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_bird_format(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    assert len(cases) == 20
    assert cases[0].kind == "public"
    assert cases[0].db_id == "db0"
    assert cases[0].expected_sql == "SELECT 0"


def test_bird_evidence_folded_into_question(tmp_path: Path) -> None:
    items = [
        {
            "question_id": 1,
            "db_id": "x",
            "question": "How many?",
            "evidence": "released refers to plan_date",
            "SQL": "SELECT 1",
        }
    ]
    cases = load_source_cases(write_json(tmp_path, "bird.json", items))
    assert "How many?" in cases[0].question
    assert "plan_date" in cases[0].question  # BIRD protocol: evidence shown to model


def test_load_spider_format(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "spider.json", SPIDER_ITEMS))
    assert cases[0].expected_sql == "SELECT count(*) FROM singer"
    assert cases[0].db_id == "concert"


def test_missing_fields_rejected(tmp_path: Path) -> None:
    bad = [{"db_id": "x", "question": "q"}]  # no SQL/query
    with pytest.raises(ValueError, match="db_id/question/SQL"):
        load_source_cases(write_json(tmp_path, "bad.json", bad))


def test_sampling_is_deterministic(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    first = sample_cases(cases, 5)
    second = sample_cases(cases, 5)
    assert [c.id for c in first] == [c.id for c in second]
    assert len(first) == 5


def test_sampling_more_than_available_returns_all(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    assert len(sample_cases(cases, 100)) == 20


def test_subset_roundtrip(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    subset = sample_cases(cases, 5)
    out = tmp_path / "subset.json"
    write_subset(subset, out)
    loaded = load_subset(out)
    assert loaded == subset


def test_exclude_keeps_dev_and_test_disjoint(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    test_set = sample_cases(cases, 5, seed=42)
    dev_set = sample_cases(cases, 5, seed=7, exclude={c.id for c in test_set})
    assert len(dev_set) == 5
    assert not ({c.id for c in dev_set} & {c.id for c in test_set})


def test_exclude_is_reproducible(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    excluded = {"db0_0", "db1_1"}
    first = sample_cases(cases, 4, seed=7, exclude=excluded)
    second = sample_cases(cases, 4, seed=7, exclude=excluded)
    assert [c.id for c in first] == [c.id for c in second]


def test_exclude_shrinks_the_pool(tmp_path: Path) -> None:
    cases = load_source_cases(write_json(tmp_path, "bird.json", BIRD_ITEMS))
    everything = {c.id for c in cases}
    assert sample_cases(cases, 5, seed=7, exclude=everything) == []


def test_shipped_subsets_are_disjoint_and_sized() -> None:
    """The committed samples are data, and their disjointness is the claim
    the whole dev/test story rests on — so it is asserted, not promised."""
    root = Path(__file__).parent.parent
    test_cases = load_subset(root / "eval" / "public" / "subset.json")
    dev_cases = load_subset(root / "eval" / "public" / "dev-subset.json")
    test_ids = {c.id for c in test_cases}
    dev_ids = {c.id for c in dev_cases}
    assert len(test_cases) == 200
    assert len(dev_cases) == 100
    assert len(test_ids) == len(test_cases), "duplicate ids in the test subset"
    assert not (test_ids & dev_ids), "dev and test must never share a question"


def test_identical_duplicate_questions_collapse(tmp_path: Path) -> None:
    # BIRD mini-dev genuinely ships the same question twice (financial_137).
    # Scoring it twice double-weights it, and case ids key both the resume
    # log and the report table.
    item = {"question_id": 7, "db_id": "db", "question": "How many?", "SQL": "SELECT 1"}
    cases = load_source_cases(write_json(tmp_path, "dup.json", [item, dict(item)]))
    assert len(cases) == 1


def test_same_id_different_content_keeps_both(tmp_path: Path) -> None:
    # A collision that is not a true duplicate must not silently lose a case.
    a = {"question_id": 7, "db_id": "db", "question": "How many?", "SQL": "SELECT 1"}
    b = {"question_id": 7, "db_id": "db", "question": "How much?", "SQL": "SELECT 2"}
    cases = load_source_cases(write_json(tmp_path, "clash.json", [a, b]))
    assert len(cases) == 2
    assert len({c.id for c in cases}) == 2, "ids must stay unique"


def _bird_source() -> Path | None:
    """The upstream question file, if this machine has it (it is too large
    to commit, so the reproducibility check skips rather than fails)."""
    for candidate in Path("/private/tmp/claude-501").glob(
        "*/*/scratchpad/minidev/MINIDEV/mini_dev_sqlite.json"
    ):
        return candidate
    return None


def test_committed_samples_are_reproducible_from_the_script() -> None:
    """The samples must be derivable, not just asserted — documenting the
    derivation as CLI flags once got it wrong, so the script is the source
    of truth and this test keeps it honest."""
    source = _bird_source()
    if source is None:
        pytest.skip("upstream BIRD question file not present on this machine")
    import importlib.util

    root = Path(__file__).parent.parent
    spec = importlib.util.spec_from_file_location(
        "rebuild_samples", root / "eval" / "public" / "rebuild_samples.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    test_cases, dev_cases = module.build(source)
    assert test_cases == load_subset(root / "eval" / "public" / "subset.json")
    assert dev_cases == load_subset(root / "eval" / "public" / "dev-subset.json")


def test_sample_derivation_carries_retired_questions_into_dev(tmp_path: Path) -> None:
    """The derivation itself — independent of the large upstream file, which
    a given machine may not have, so this must not depend on it."""
    import importlib.util

    root = Path(__file__).parent.parent
    spec = importlib.util.spec_from_file_location(
        "rebuild_samples", root / "eval" / "public" / "rebuild_samples.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    items = [
        {"question_id": i, "db_id": f"db{i % 3}", "question": f"q{i}", "SQL": f"SELECT {i}"}
        for i in range(60)
    ]
    source = write_json(tmp_path, "pool.json", items)
    retired = {f"db{i % 3}_{i}" for i in range(10)}

    test_cases, dev_cases = module.build(
        source, retired=retired, test_size=20, dev_size=15
    )

    test_ids = {c.id for c in test_cases}
    dev_ids = {c.id for c in dev_cases}
    assert len(test_cases) == 20 and len(dev_cases) == 15
    assert not (test_ids & dev_ids), "dev and test must be disjoint"
    assert not (test_ids & retired), "the sealed set must exclude observed questions"
    assert retired <= dev_ids, "retired questions are carried into dev, not discarded"
