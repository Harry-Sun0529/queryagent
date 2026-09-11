"""What a result covers, from the newest record in the data (T37).

The demo data ends on 2026-08-22. Asked in September, 「上个月」 is 22 days
of data reported under a 31-day heading, and 「本月」 is empty for a reason
the result never gave. Both are claims a reader acts on: that the month was
whole, and that the business did nothing.

The system knows one fact that settles most of this — the newest record's
date — and says only that. It does not know whether that last day finished
loading, so it says that too. Wording lives here, as pure functions, so the
claims can be tested without a database.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from queryagent.workflow.periods import Period


def latest_date(value: object) -> date | None:
    """The date of a ``MAX(time_column)`` value, whatever the driver returned.

    MySQL and ClickHouse give ``datetime``; SQLite gives the stored text. An
    empty table gives NULL, and anything unrecognisable is treated as
    unknown rather than guessed at.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def describe_coverage(period: Period | None, latest: date | None, *, probed: bool) -> str:
    """One note on whether the data reaches as far as the period does, or ''.

    ``probed`` is False when the mapping has no time column to read: then
    nothing is claimed either way. A probe that ran but found nothing usable
    is said out loud, because silence would read as "covered".
    """
    if not probed:
        return ""
    if latest is None:
        return "未能确定库中最新一条记录的日期，无法判断统计区间是否已有完整数据。"
    if period is None:
        return f"库中最新一条记录在 {latest}；以上是截至那天的全部数据。"
    if latest < period.start:
        return (
            f"没有数据：库中最新一条记录在 {latest}，早于统计区间的开始 {period.start}；"
            "整个区间都还没有数据，结果不代表业务为 0。"
        )
    if latest < period.end:
        missing = (period.end - latest).days
        return (
            f"数据不完整：库中最新一条记录在 {latest}，统计区间 {period.start} 至 {period.end} 的"
            f"最后 {missing} 天（{latest + timedelta(days=1)} 起）没有任何数据。这个结果只覆盖 "
            f"{period.start} 至 {latest}，不是完整区间；{latest} 当天也可能尚未完整。"
        )
    if latest == period.end:
        return f"库中最新一条记录在 {latest}，正是统计区间的最后一天；那天的数据可能尚未完整。"
    return f"统计区间已被数据覆盖（库中最新一条记录在 {latest}）。"


def describe_emptiness(
    rows: tuple[tuple[object, ...], ...], period: Period | None, latest: date | None
) -> str:
    """Say so when there is nothing to report, and why if the data says (P10, F5).

    SUM over no rows is NULL. Printed bare it reads as an error; read as 0 it
    is a claim that the business made nothing. When the whole period lies
    after the newest record, "no matching records" is also wrong — there was
    nothing to match. COUNT's 0 is a real answer and gets no note here; the
    coverage note says when that 0 is only an absence of data.
    """
    # Short on purpose: the coverage note printed next says where the data
    # ends and why this is not 0; saying it twice is noise.
    beyond = period is not None and latest is not None and latest < period.start
    if not rows:
        # A grouped query over a period with no data returns no groups at all.
        return "结果为空：统计区间内还没有数据" if beyond else "查询没有返回任何行"
    if all(value is None for row in rows for value in row):
        if beyond:
            return "结果为空：统计区间内还没有数据"
        return "结果为空：该统计区间内没有匹配的记录。空不等于 0"
    return ""
