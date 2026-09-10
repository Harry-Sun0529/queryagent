"""Time expressions in a question → an absolute, confirmable date range.

「上个月」 is a 口径 choice in disguise, and so is 「本月」 (the whole month, or
the month so far?) and 「近7天」 (including today?). This module makes one
choice per expression, and the confirmation sheet shows the absolute dates
that choice produced, so a person confirms what will actually run.

Deliberately a closed set, parsed deterministically. A question naming two
different periods, or an impossible date, raises :class:`PeriodError`
rather than picking one: a guessed period is a wrong number that looks
exactly like a right one. Callers turn the refusal into a gap to ask about.

Relative expressions are resolved when the draft is prepared and the result
is stored as absolute dates, so a confirmation made today still runs today's
range if it is executed tomorrow (§9.3).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta


class PeriodError(ValueError):
    """A time expression that cannot become exactly one range."""


_CANONICAL = re.compile(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class Period:
    """An inclusive date range: both ``start`` and ``end`` are counted."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise PeriodError(f"区间结束早于开始：{self.start} 至 {self.end}")

    @property
    def end_exclusive(self) -> date:
        """The day after ``end``. SQL compares timestamps, so the last day must
        be bounded by the next midnight, not by ``end`` itself."""
        return self.end + timedelta(days=1)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def encode(self) -> str:
        """The canonical string stored in a rule and hashed into a confirmation."""
        return f"{self.start.isoformat()}..{self.end.isoformat()}"

    @classmethod
    def decode(cls, text: str) -> Period:
        """Inverse of :meth:`encode`; anything else is refused."""
        match = _CANONICAL.fullmatch(text)
        if match is None:
            raise ValueError(f"not a canonical period: {text!r}")
        return cls(date.fromisoformat(match.group(1)), date.fromisoformat(match.group(2)))

    def render(self) -> str:
        return f"{self.start.isoformat()} 至 {self.end.isoformat()}（{self.days} 天）"


@dataclass(frozen=True)
class FoundPeriod:
    """A period and the words in the question it was read from."""

    period: Period
    phrase: str


# ------------------------------------------------------------------ helpers

_CN_DIGITS = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}


def _number(text: str) -> int | None:
    """Arabic or small Chinese numerals (一 … 九十九)."""
    if text.isdigit():
        return int(text)
    if "十" in text:
        tens, _, ones = text.partition("十")
        high = _CN_DIGITS.get(tens) if tens else 1
        low = _CN_DIGITS.get(ones) if ones else 0
        return None if high is None or low is None else high * 10 + low
    return _CN_DIGITS.get(text) if len(text) == 1 else None


def _day(year: str, month: str, day: str, phrase: str) -> date:
    try:
        return date(int(year), int(month), int(day))
    except ValueError as exc:
        raise PeriodError(f"不可能的日期：{phrase}") from exc


def _month(year: int, month: int) -> Period:
    start = date(year, month, 1)
    following = date(year + (month == 12), month % 12 + 1, 1)
    return Period(start, following - timedelta(days=1))


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


# ------------------------------------------------------------------ patterns

Handler = Callable[[re.Match[str], date], "Period | None"]

_NUM = r"(\d{1,3}|[一二两三四五六七八九十]{1,3})"


def _explicit_range(m: re.Match[str], today: date) -> Period:
    start = _day(m.group(1), m.group(2), m.group(3), m.group(0))
    end = _day(m.group(4), m.group(5), m.group(6), m.group(0))
    return Period(start, end)


def _single_day(m: re.Match[str], today: date) -> Period:
    day = _day(m.group(1), m.group(2), m.group(3), m.group(0))
    return Period(day, day)


def _year_month(m: re.Match[str], today: date) -> Period | None:
    month = int(m.group(2))
    return _month(int(m.group(1)), month) if 1 <= month <= 12 else None


def _last_n_days(m: re.Match[str], today: date) -> Period | None:
    count = _number(m.group(1))
    if not count:
        return None
    return Period(today - timedelta(days=count - 1), today)


def _bare_month(m: re.Match[str], today: date) -> Period | None:
    month = _number(m.group(1))
    if month is None or not 1 <= month <= 12:
        return None
    # The most recent such month that is not in the future.
    return _month(today.year if month <= today.month else today.year - 1, month)


def _previous_month(m: re.Match[str], today: date) -> Period:
    first = today.replace(day=1)
    last_of_previous = first - timedelta(days=1)
    return _month(last_of_previous.year, last_of_previous.month)


def _this_month(m: re.Match[str], today: date) -> Period:
    return Period(today.replace(day=1), today)


def _previous_week(m: re.Match[str], today: date) -> Period:
    return Period(_monday(today) - timedelta(days=7), _monday(today) - timedelta(days=1))


def _this_week(m: re.Match[str], today: date) -> Period:
    return Period(_monday(today), today)


def _previous_year(m: re.Match[str], today: date) -> Period:
    return Period(date(today.year - 1, 1, 1), date(today.year - 1, 12, 31))


def _this_year(m: re.Match[str], today: date) -> Period:
    return Period(date(today.year, 1, 1), today)


def _days_ago(count: int) -> Handler:
    def handler(m: re.Match[str], today: date) -> Period:
        day = today - timedelta(days=count)
        return Period(day, day)

    return handler


_PATTERNS: tuple[tuple[re.Pattern[str], Handler], ...] = (
    (
        re.compile(
            r"(\d{4})-(\d{1,2})-(\d{1,2})\s*(?:\.\.|到|至|~|～)\s*(\d{4})-(\d{1,2})-(\d{1,2})"
        ),
        _explicit_range,
    ),
    (re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"), _single_day),
    (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"), _single_day),
    (re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月"), _year_month),
    (re.compile(r"(?<!\d)(\d{4})-(\d{1,2})(?![\d-])"), _year_month),
    (re.compile(r"(?:最近|近|过去)" + _NUM + r"\s*天"), _last_n_days),
    (re.compile(r"上个?月|上一个月"), _previous_month),
    (re.compile(r"本月|这个月|当月"), _this_month),
    (re.compile(r"上周|上一周|上个星期"), _previous_week),
    (re.compile(r"本周|这周|这一周|这个星期"), _this_week),
    (re.compile(r"去年|上一年"), _previous_year),
    (re.compile(r"今年|本年"), _this_year),
    (re.compile(r"昨天|昨日"), _days_ago(1)),
    # 「目前天气」 contains 前天; the lookbehind keeps it from meaning a date.
    (re.compile(r"(?<![目之提])前天"), _days_ago(2)),
    (re.compile(r"今天|今日"), _days_ago(0)),
    (re.compile(r"(?<![\d年\-])(\d{1,2}|[一二三四五六七八九十]{1,3})月份?"), _bare_month),
)


def find_period(question: str, today: date) -> FoundPeriod | None:
    """The one period a question names, or None when it names none.

    Patterns run most-specific first and a later match overlapping an earlier
    one is ignored, so 「2026年8月」 is one month rather than a year-month plus
    a bare 「8月」. The same period said twice (「上个月（2026年8月）」) is one
    period; two different ones are refused.

    Raises:
        PeriodError: Two different periods, or an impossible date.
    """
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, FoundPeriod]] = []
    for pattern, handler in _PATTERNS:
        for match in pattern.finditer(question):
            start, end = match.span()
            if any(start < right and left < end for left, right in taken):
                continue
            period = handler(match, today)
            if period is None:
                continue
            taken.append((start, end))
            found.append((start, FoundPeriod(period, match.group(0))))
    if not found:
        return None
    found.sort(key=lambda pair: pair[0])
    distinct = {item.period for _, item in found}
    if len(distinct) > 1:
        phrases = "、".join(item.phrase for _, item in found)
        raise PeriodError(
            f"问题里有多个不同的统计区间：{phrases}。一次只能算一个区间，请只保留一个。"
        )
    return found[0][1]


def parse_period(text: str, today: date) -> Period:
    """A period stated on purpose (``--period`` or at a prompt): exactly one.

    Raises:
        PeriodError: Nothing recognisable, or more than one period.
    """
    found = find_period(text, today)
    if found is None:
        raise PeriodError(
            f"无法识别的统计区间：{text!r}。可以写：上个月 / 本月 / 上周 / 最近7天 / "
            "2026-08 / 2026-08-01..2026-08-31"
        )
    return found.period
