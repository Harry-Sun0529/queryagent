"""Slice 1C: time expressions become an absolute, confirmable range.

A time expression is a 口径 choice in disguise: 「本月」 could mean the whole
month or the month so far, 「近7天」 could include today or not. The parser
makes one choice per expression and the confirmation sheet shows the
absolute dates, so a person confirms what will actually run. What it does
not recognise, or finds twice, it refuses — the caller turns that into a gap
to ask about, never a guess.

Today is fixed at Thursday 2026-09-10 unless a test says otherwise.
"""

from __future__ import annotations

from datetime import date

import pytest

from queryagent.workflow.periods import Period, PeriodError, find_period, parse_period

TODAY = date(2026, 9, 10)  # a Thursday


def _range(text: str, today: date = TODAY) -> tuple[str, str]:
    found = find_period(text, today)
    assert found is not None, text
    return found.period.start.isoformat(), found.period.end.isoformat()


# ------------------------------------------------------------ relative


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("上个月新增用户有多少", ("2026-08-01", "2026-08-31")),
        ("上月成交额", ("2026-08-01", "2026-08-31")),
        ("本月的成交额", ("2026-09-01", "2026-09-10")),
        ("这个月拉新多少", ("2026-09-01", "2026-09-10")),
        ("上周的活跃买家", ("2026-08-31", "2026-09-06")),
        ("本周新增", ("2026-09-07", "2026-09-10")),
        ("昨天成交额", ("2026-09-09", "2026-09-09")),
        ("前天的订单", ("2026-09-08", "2026-09-08")),
        ("今天到现在的新增", ("2026-09-10", "2026-09-10")),
        ("去年成交额", ("2025-01-01", "2025-12-31")),
        ("今年成交额", ("2026-01-01", "2026-09-10")),
        ("最近7天新增用户", ("2026-09-04", "2026-09-10")),
        ("近七天的活跃买家", ("2026-09-04", "2026-09-10")),
        ("过去30天的成交额", ("2026-08-12", "2026-09-10")),
        ("近三十天", ("2026-08-12", "2026-09-10")),
    ],
)
def test_relative_expressions_resolve_against_today(text: str, expected: tuple[str, str]) -> None:
    assert _range(text) == expected


def test_last_month_in_january_is_december_of_the_previous_year() -> None:
    assert _range("上个月", date(2026, 1, 15)) == ("2025-12-01", "2025-12-31")


def test_last_week_starts_on_monday_even_when_today_is_monday() -> None:
    assert _range("上周", date(2026, 9, 7)) == ("2026-08-31", "2026-09-06")


# ------------------------------------------------------------ absolute


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026年8月新增用户", ("2026-08-01", "2026-08-31")),
        ("2026-08 的成交额", ("2026-08-01", "2026-08-31")),
        ("2026-02 的成交额", ("2026-02-01", "2026-02-28")),
        ("2024-02 的成交额", ("2024-02-01", "2024-02-29")),
        ("2026-08-15 当天", ("2026-08-15", "2026-08-15")),
        ("2026年8月15日", ("2026-08-15", "2026-08-15")),
        ("2026-08-01..2026-08-15 的新增", ("2026-08-01", "2026-08-15")),
        ("2026-08-01到2026-08-15", ("2026-08-01", "2026-08-15")),
        ("从2026-08-01至2026-08-15", ("2026-08-01", "2026-08-15")),
    ],
)
def test_absolute_expressions(text: str, expected: tuple[str, str]) -> None:
    assert _range(text) == expected


def test_a_bare_month_is_the_most_recent_one_not_in_the_future() -> None:
    assert _range("8月新增用户") == ("2026-08-01", "2026-08-31")
    assert _range("十二月的成交额") == ("2025-12-01", "2025-12-31")


# ------------------------------------------------------ refusals (P2)


def test_no_time_expression_is_none_not_all_time() -> None:
    assert find_period("新增用户有多少", TODAY) is None


def test_two_different_periods_are_ambiguous_not_the_first_one() -> None:
    """「上个月和本月」 is a comparison this slice cannot run; guessing one is worse."""
    with pytest.raises(PeriodError, match="上个月") as refused:
        find_period("上个月和本月的新增对比", TODAY)
    assert "本月" in str(refused.value)


def test_the_same_period_said_twice_is_not_ambiguous() -> None:
    assert _range("上个月（2026年8月）新增用户") == ("2026-08-01", "2026-08-31")


def test_an_impossible_date_is_refused_rather_than_skipped() -> None:
    """Dropping it silently would turn 「2026-02-30」 into an unbounded query."""
    with pytest.raises(PeriodError, match="2026-02-30"):
        find_period("2026-02-30 的成交额", TODAY)


def test_a_range_that_ends_before_it_starts_is_refused() -> None:
    with pytest.raises(PeriodError):
        find_period("2026-08-15..2026-08-01", TODAY)


def test_an_expression_that_names_the_future_only_is_not_invented() -> None:
    """下个月 is not in the supported set: no period rather than a guess."""
    assert find_period("下个月的预算", TODAY) is None


# ------------------------------------------------------------ encoding


def test_encode_and_decode_round_trip() -> None:
    period = Period(date(2026, 8, 1), date(2026, 8, 31))
    assert period.encode() == "2026-08-01..2026-08-31"
    assert Period.decode(period.encode()) == period


@pytest.mark.parametrize("text", ["", "上个月", "2026-08-01", "2026-08-31..2026-08-01"])
def test_decode_accepts_only_the_canonical_form(text: str) -> None:
    with pytest.raises(ValueError):
        Period.decode(text)


def test_render_is_what_a_person_reads_on_the_sheet() -> None:
    rendered = Period(date(2026, 8, 1), date(2026, 8, 31)).render()
    assert rendered == "2026-08-01 至 2026-08-31（31 天）"


def test_the_exclusive_end_is_the_day_after() -> None:
    """SQL compares timestamps; the last day must be included in full."""
    assert Period(date(2026, 8, 1), date(2026, 8, 31)).end_exclusive == date(2026, 9, 1)


# ------------------------------------------------------------ parse_period


def test_parse_period_accepts_one_expression() -> None:
    assert parse_period("上个月", TODAY) == Period(date(2026, 8, 1), date(2026, 8, 31))
    assert parse_period("2026-08-01..2026-08-15", TODAY).end == date(2026, 8, 15)


def test_parse_period_refuses_what_it_cannot_read_and_says_what_it_can() -> None:
    with pytest.raises(PeriodError, match="上个月"):
        parse_period("随便哪段时间", TODAY)
