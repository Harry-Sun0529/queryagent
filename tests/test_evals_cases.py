"""Unit tests for eval case loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from queryagent.evals.cases import load_cases

CASES_YAML = """\
cases:
  - id: c1
    kind: simple
    question: 一共有多少用户？
    expected_sql: SELECT count(*) FROM users
    tags: [count]
  - id: c2
    kind: clarify
    question: 上个月新增用户有多少？
    expected_metrics: [new_users]
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "cases.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_cases_load(tmp_path: Path) -> None:
    cases = load_cases(write(tmp_path, CASES_YAML))
    assert [c.id for c in cases] == ["c1", "c2"]
    assert cases[0].tags == ("count",)
    assert cases[1].expected_metrics == ("new_users",)


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    text = CASES_YAML.replace("id: c2", "id: c1")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(write(tmp_path, text))


def test_unknown_kind_rejected(tmp_path: Path) -> None:
    text = CASES_YAML.replace("kind: simple", "kind: fancy")
    with pytest.raises(ValueError, match="kind"):
        load_cases(write(tmp_path, text))


def test_expected_sql_required_for_result_cases(tmp_path: Path) -> None:
    text = CASES_YAML.replace("    expected_sql: SELECT count(*) FROM users\n", "")
    with pytest.raises(ValueError, match="expected_sql"):
        load_cases(write(tmp_path, text))


def test_clarify_requires_expected_metrics(tmp_path: Path) -> None:
    text = CASES_YAML.replace("    expected_metrics: [new_users]\n", "")
    with pytest.raises(ValueError, match="expected_metrics"):
        load_cases(write(tmp_path, text))


def test_shipped_scaffold_is_valid() -> None:
    cases = load_cases(Path(__file__).parent.parent / "eval" / "cases.yaml")
    assert len(cases) >= 5
    kinds = {c.kind for c in cases}
    assert "clarify" in kinds and "no_clarify" in kinds
