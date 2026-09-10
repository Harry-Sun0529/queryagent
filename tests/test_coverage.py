"""T37: what a result covers, said in words, from the newest record in the data.

Pure functions only; test_workflow_service.py proves the probe is recorded
on the run, test_cli_flow.py that the words reach the user, and the
integration files that each driver's MAX() comes back as a date.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from queryagent.workflow.coverage import describe_coverage, describe_emptiness, latest_date
from queryagent.workflow.periods import Period

AUGUST = Period(date(2026, 8, 1), date(2026, 8, 31))
SEPTEMBER_SO_FAR = Period(date(2026, 9, 1), date(2026, 9, 10))
DEMO_LATEST = date(2026, 8, 22)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 8, 22, 11, 4, 36), date(2026, 8, 22)),  # MySQL / ClickHouse DateTime
        (date(2026, 8, 22), date(2026, 8, 22)),
        ("2026-08-22 11:04:36", date(2026, 8, 22)),  # SQLite text
        ("2026-08-22", date(2026, 8, 22)),
        (None, None),  # an empty table
        (42, None),
        ("not a date", None),
    ],
)
def test_the_newest_record_is_read_as_a_date_whatever_the_driver_returns(
    value: object, expected: date | None
) -> None:
    assert latest_date(value) == expected


def test_a_period_that_runs_past_the_data_says_which_days_are_missing() -> None:
    """F4: the demo's 「上个月」 asked in September is 22 days, not a month."""
    note = describe_coverage(AUGUST, DEMO_LATEST, probed=True)
    assert "数据不完整" in note
    assert "最后 9 天（2026-08-23 起）没有任何数据" in note
    assert "只覆盖 2026-08-01 至 2026-08-22" in note
    assert "2026-08-22 当天也可能尚未完整" in note


def test_a_period_wholly_after_the_data_is_no_data_rather_than_zero() -> None:
    """F5: 「本月」 on data that ends 08-22."""
    note = describe_coverage(SEPTEMBER_SO_FAR, DEMO_LATEST, probed=True)
    assert "早于统计区间的开始 2026-09-01" in note
    assert "不代表业务为 0" in note


def test_a_covered_period_is_said_to_be_covered_and_nothing_more() -> None:
    note = describe_coverage(AUGUST, date(2026, 9, 5), probed=True)
    assert "已被数据覆盖" in note
    assert "不完整" not in note


def test_data_ending_on_the_last_day_warns_that_day_may_be_partial() -> None:
    note = describe_coverage(AUGUST, date(2026, 8, 31), probed=True)
    assert "正是统计区间的最后一天" in note
    assert "可能尚未完整" in note


def test_without_a_period_the_note_dates_the_whole_data() -> None:
    assert "截至那天的全部数据" in describe_coverage(None, DEMO_LATEST, probed=True)


def test_a_probe_that_found_nothing_usable_says_so() -> None:
    assert "未能确定" in describe_coverage(AUGUST, None, probed=True)


def test_no_probe_means_no_claim_either_way() -> None:
    """A whole-statement mapping has no time column to probe; silence, not a guess."""
    assert describe_coverage(AUGUST, None, probed=False) == ""


def test_an_empty_result_after_the_data_ends_is_explained_as_no_data() -> None:
    """F5: not 「该统计区间内没有匹配的记录」 — there was nothing to match."""
    note = describe_emptiness(((None,),), SEPTEMBER_SO_FAR, DEMO_LATEST)
    assert "没有数据" in note
    assert "没有匹配的记录" not in note


def test_an_empty_result_inside_the_data_is_no_matching_records() -> None:
    note = describe_emptiness(((None,),), AUGUST, date(2026, 9, 5))
    assert "该统计区间内没有匹配的记录" in note
    assert "空不等于 0" in note


def test_a_count_of_zero_is_an_answer_and_gets_no_emptiness_note() -> None:
    assert describe_emptiness(((0,),), AUGUST, DEMO_LATEST) == ""


def test_no_rows_at_all_is_said_plainly() -> None:
    assert describe_emptiness((), AUGUST, DEMO_LATEST) == "查询没有返回任何行"
