"""Sanity check: every expected_sql in eval/cases.yaml runs on the demo db.

Guards against reference-SQL typos silently corrupting eval numbers.
Skipped when demo_shop.db has not been generated (CI); run `make demo-data`
locally first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.evals.cases import load_cases
from queryagent.safety import ensure_safe_select

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "examples" / "demo_ecommerce" / "demo_shop.db"

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason="demo_shop.db not generated (make demo-data)"
)

CASES = load_cases(ROOT / "eval" / "cases.yaml")
RESULT_CASES = [case for case in CASES if case.expected_sql]


def test_case_mix_matches_spec() -> None:
    kinds = [case.kind for case in CASES]
    assert len(CASES) == 20
    assert kinds.count("clarify") >= 2
    assert kinds.count("no_clarify") >= 2
    assert kinds.count("metric") >= 4
    assert kinds.count("multistep") >= 4


@pytest.mark.parametrize("case", RESULT_CASES, ids=lambda c: c.id)
def test_expected_sql_is_safe_and_runs(case) -> None:  # type: ignore[no-untyped-def]
    ensure_safe_select(case.expected_sql)  # reference SQL must pass our own gate
    connector = SQLiteConnector(path=str(DB_PATH))
    try:
        result = connector.execute(case.expected_sql, timeout_s=10, max_rows=500)
    finally:
        connector.close()
    assert result.rows, f"{case.id}: expected_sql returned no rows (stale demo data?)"
    first_cell = result.rows[0][0]
    if len(result.rows) == 1 and isinstance(first_cell, (int, float)):
        assert first_cell is not None
