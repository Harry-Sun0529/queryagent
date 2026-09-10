"""「每天」「按渠道」 → how a result is split, as a confirmable rule (T38).

Same shape as periods.py, for the same reason: a grouping decides whether
the answer is one number or a table, so it is part of the 口径 and belongs
on the confirmation sheet. A closed set, parsed deterministically. Anything
outside it — 「日均」, 「每小时」, two different splits — raises
:class:`GroupingError` instead of being read as the nearest thing it
resembles: 「日均」 read as 「每天」 is a table posing as an average, and read
as nothing it is a total posing as one.

Time grains are fixed here; dimensions are declared by a maintainer, per
table, in the mappings file. Words for a dimension nobody declared are not
recognised at all — the system cannot know that 「按渠道」 was a request to
split — which is a limit the docs state rather than a guess this code makes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from queryagent.workflow.periods import Period


class GroupingError(ValueError):
    """A split the question asks for that cannot become exactly one grouping."""


DAY = "day"
WEEK = "week"
MONTH = "month"
NONE = "none"
TIME_GRAINS = (DAY, WEEK, MONTH)
DIMENSION_PREFIX = "dim:"

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class Dimension:
    """A maintainer-declared way to split a result.

    ``columns`` pairs a table with the column holding this dimension there.
    A metric whose mapping reads a table not listed cannot be split by it —
    the compiler refuses rather than join its way to an answer.
    """

    key: str
    label: str
    aliases: tuple[str, ...] = ()
    columns: tuple[tuple[str, str], ...] = ()

    def column_for(self, table: str) -> str | None:
        return dict(self.columns).get(table)


@dataclass(frozen=True)
class FoundGrouping:
    """A grouping and the words in the question it was read from."""

    value: str
    phrase: str


def is_grouping(value: str) -> bool:
    """True for a canonical rule value; anything else never reaches SQL."""
    if value in (*TIME_GRAINS, NONE):
        return True
    return value.startswith(DIMENSION_PREFIX) and bool(
        _IDENTIFIER.fullmatch(value[len(DIMENSION_PREFIX) :])
    )


_TEXT = {
    DAY: "按天（每个日期一行）",
    WEEK: "按周（周一起算，每周一行）",
    MONTH: "按月（每月一行）",
    NONE: "不分组（一个总数）",
}


def grouping_text(value: str, labels: Mapping[str, str] | None = None) -> str:
    """How a grouping reads on the confirmation sheet.

    ``labels`` maps a dimension key to the name its maintainer gave it: a
    sheet reading 「按 channel」 is not one an operator can repeat (D04).
    Without it the key is shown, which is still unambiguous.
    """
    if value.startswith(DIMENSION_PREFIX):
        key = value[len(DIMENSION_PREFIX) :]
        return f"按「{(labels or {}).get(key, key)}」（每个取值一行）"
    return _TEXT.get(value, value)


# Asked for, but not a split this system makes. Checked before anything else
# so 「每天平均」 cannot be half-read as 「每天」.
_UNSUPPORTED = re.compile(
    r"日均|周均|月均|平均每[天日周月]|每[天日周月]平均|每小时|按小时|每季度|按季度|每年|按年"
)
_TIME_PATTERNS = (
    (re.compile(r"每一?天|每日|按天|按日|逐日|分天|分日"), DAY),
    (re.compile(r"每一?周|每个?星期|按周|逐周|分周"), WEEK),
    (re.compile(r"每一?个?月|按月|逐月|分月"), MONTH),
)
_SPLIT_WORDS = r"(?:按|分|各|每一个|每个|不同)\s*"


def _dimension_pattern(dimension: Dimension) -> re.Pattern[str]:
    names = sorted({dimension.label, *dimension.aliases}, key=len, reverse=True)
    return re.compile(_SPLIT_WORDS + "(?:" + "|".join(re.escape(n) for n in names) + ")")


def find_grouping(question: str, dimensions: tuple[Dimension, ...] = ()) -> FoundGrouping | None:
    """The one grouping a question asks for, or None when it asks for none.

    Raises:
        GroupingError: A split this system does not make (「日均」, 「每小时」),
            or two different ones (「每天各渠道」).
    """
    unsupported = _UNSUPPORTED.search(question)
    if unsupported:
        raise GroupingError(
            f"「{unsupported.group(0)}」不是这里能做的分组：日均等是另一个指标，按小时 / 季度 / "
            "年分组尚不支持。可以按天 / 周 / 月或维护者声明的维度分组；要一个总数请写不分组。"
        )
    found: list[tuple[int, FoundGrouping]] = []
    for pattern, value in _TIME_PATTERNS:
        found.extend(
            (m.start(), FoundGrouping(value, m.group(0))) for m in pattern.finditer(question)
        )
    for dimension in dimensions:
        found.extend(
            (m.start(), FoundGrouping(f"{DIMENSION_PREFIX}{dimension.key}", m.group(0)))
            for m in _dimension_pattern(dimension).finditer(question)
        )
    if not found:
        return None
    found.sort(key=lambda pair: pair[0])
    if len({item.value for _, item in found}) > 1:
        phrases = "、".join(item.phrase for _, item in found)
        raise GroupingError(
            f"问题里有多个不同的分组方式：{phrases}。一次只支持一种分组，请只保留一个。"
        )
    return found[0][1]


def parse_grouping(text: str, dimensions: tuple[Dimension, ...] = ()) -> str:
    """A grouping stated on purpose (``--group-by`` or at a prompt).

    Accepts the canonical values, a dimension's key, label or alias, or the
    same words a question would use.

    Raises:
        GroupingError: Nothing recognisable, or more than one grouping.
    """
    text = text.strip()
    if text in (NONE, "不分组", "总数"):
        return NONE
    if text in TIME_GRAINS:
        return text
    for dimension in dimensions:
        if text in (dimension.key, dimension.label, *dimension.aliases):
            return f"{DIMENSION_PREFIX}{dimension.key}"
    found = find_grouping(text, dimensions)
    if found is None:
        names = " / ".join(d.label for d in dimensions)
        raise GroupingError(
            f"无法识别的分组方式：{text!r}。可以写：day / week / month / none"
            + (f"，或维度：{names}" if names else "")
        )
    return found.value


def bucket_start(day: date, grain: str) -> date:
    """The first day of the group ``day`` falls in — what the SQL returns as its key."""
    if grain == WEEK:
        return day - timedelta(days=day.weekday())
    if grain == MONTH:
        return day.replace(day=1)
    return day


def bucket_starts(period: Period, grain: str) -> tuple[date, ...]:
    """Every group a period touches, in order, including partial ones at the edges."""
    starts = []
    current = bucket_start(period.start, grain)
    while current <= period.end:
        starts.append(current)
        if grain == WEEK:
            current += timedelta(days=7)
        elif grain == MONTH:
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            current += timedelta(days=1)
    return tuple(starts)


def edges_are_partial(period: Period, grain: str) -> bool:
    """True when the first or last group reaches outside the period.

    Only rows inside the period are counted, so such a group is a partial
    week or month and must be said to be one.
    """
    if grain not in (WEEK, MONTH):
        return False
    after = period.end + timedelta(days=1)
    return bucket_start(period.start, grain) != period.start or bucket_start(after, grain) != after
