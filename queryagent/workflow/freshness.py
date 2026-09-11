"""What the sheet can say about the data's reach before anyone confirms (T41, ADR-010).

v0.8 said it only on the result: finding out how far the data reaches takes
a query, and nothing ran before confirmation (I2). ADR-010 narrows that rule
to "no *business* query before confirmation" and gives two ways to warn
earlier:

- ``declared`` (the default): the maintainer states each mapping's update
  cadence — ``freshness: {lag_days: 1}`` for T+1 — and the sheet works out
  from today's date what should be there. Zero queries.
- ``probe``: a maintainer who wants the fact rather than the promise lets
  the compiler's own ``SELECT MAX(time_column)`` run before confirmation,
  with a short timeout, cached, charged to the budget.

Either way the note is advice. It is not stored on the draft and not in its
hash — a probe's answer changes as data loads, and a confirmation must not
expire because it did — and the result still reports what the probe at
execution time found.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo

from queryagent.connectors.base import QueryResult
from queryagent.workflow.compiler import CompiledQuery
from queryagent.workflow.coverage import latest_date
from queryagent.workflow.periods import Period

DECLARED = "declared"
PROBE = "probe"
OFF = "off"

PROBE_FAILED = (
    "确认前未能探测库中最新一条记录的日期（探测失败、超时或预算不足）；"
    "执行后的结果会说明数据覆盖到哪天。"
)


@dataclass(frozen=True)
class FreshnessPolicy:
    """How much the sheet may learn about the data's reach before confirmation.

    Built from the ``workflow.freshness_*`` config. ``probe`` is a
    short-timeout executor and exists only in ``probe`` mode: the one kind of
    statement allowed before a confirmation (ADR-010). ``today`` is the
    business day a declared cadence counts back from; ``zone`` stamps the
    time a probe was read.
    """

    mode: str = DECLARED
    today: Callable[[], date] = date.today
    probe: Callable[[CompiledQuery], QueryResult] | None = None
    cache_minutes: int = 10
    zone: tzinfo = timezone.utc


def expected_latest(today: date, lag_days: int) -> date:
    """The newest day a T+``lag_days`` table should hold on ``today``."""
    return today - timedelta(days=lag_days)


def describe_declared(period: Period, lag_days: int, today: date) -> str:
    """What a declared cadence implies for this period, or '' when it should all be there."""
    expected = expected_latest(today, lag_days)
    head = f"维护者声明该表按 T+{lag_days} 更新，预计最新数据到 {expected}"
    if expected < period.start:
        return f"{head}：整个统计区间可能都还没有数据。"
    if expected < period.end:
        missing = (period.end - expected).days
        return (
            f"{head}：统计区间最后 {missing} 天（{expected + timedelta(days=1)} 起）"
            "可能还没有数据。"
        )
    return ""


def describe_probed(period: Period, latest: date, probed_at: datetime, zone: tzinfo) -> str:
    """What a probe before confirmation found, marked as advice with the time it was read."""
    head = f"库中最新一条记录在 {latest}（{probed_at.astimezone(zone):%H:%M} 探测，仅供参考）"
    if latest < period.start:
        return f"{head}，早于统计区间的开始 {period.start}：整个区间都还没有数据。"
    if latest < period.end:
        missing = (period.end - latest).days
        return (
            f"{head}：统计区间最后 {missing} 天（{latest + timedelta(days=1)} 起）还没有数据。"
        )
    return f"{head}：统计区间内已有数据。"


def describe_lag(expected_through: str, data_through: str) -> str:
    """Name a table further behind than its maintainer said it would be, or ''.

    Read from a run, after execution: what the declaration expected then,
    against what the probe found then.
    """
    expected = latest_date(expected_through)
    latest = latest_date(data_through)
    if expected is None or latest is None or latest >= expected:
        return ""
    return (
        f"数据比维护者声明的更新节奏滞后 {(expected - latest).days} 天：按声明应有到 {expected} "
        f"的数据，库中最新一条记录在 {latest}，可能是数据加载延迟。"
    )
