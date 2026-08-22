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


def test_case_mix_carries_enough_weight_per_metric() -> None:
    """Minimums per kind, not a magic total.

    Each reported rate needs a denominator big enough to say anything: at
    four cases a "4/4" is a nice-sounding number with no evidence behind it.
    Clarify behaviour is this project's differentiator, so its two arms —
    should-ask and must-not-ask — carry the largest minimums.
    """
    kinds = [case.kind for case in CASES]
    assert kinds.count("clarify") >= 8, "should-ask arm too small to mean anything"
    assert kinds.count("no_clarify") >= 8, "must-not-ask control too small"
    assert kinds.count("metric") >= 8, "metric-citation rate needs a real denominator"
    assert kinds.count("multistep") >= 4
    assert kinds.count("simple") >= 8


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
