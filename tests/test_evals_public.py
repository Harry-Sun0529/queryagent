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
