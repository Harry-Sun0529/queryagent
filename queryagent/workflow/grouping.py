"""「每天」「按渠道」 → how a result is split, as a confirmable rule (T38).

Same shape as periods.py, for the same reason: a grouping decides whether
the answer is one number or a table, so it is part of the 口径 and belongs
on the confirmation sheet. A closed set, parsed deterministically. Anything
outside it — 「日均」, 「每小时」, two different splits — raises
:class:`GroupingError` instead of being read as the nearest thing it
resembles: 「日均」 read as 「每天」 is a table posing as an average, and read
as nothing it is a total posing as one.

Time grains are fixed here; dimensions are declared by a maintainer, per
table, in the mappings file. A split by something nobody declared is asked
about when the question says it in an explicit shape (「各城市的」,
「按城市分组」); looser phrasings of an undeclared split are not recognised,
which is a limit the docs state rather than a guess this code makes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from queryagent.errors import AnswerError
from queryagent.workflow.periods import Period


class GroupingError(AnswerError):
    """A split the question asks for that cannot become exactly one grouping."""

    def __init__(self, message: str, *, undeclared: bool = False) -> None:
        super().__init__(message)
        self.undeclared = undeclared


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
    values: tuple[tuple[str, tuple[str, ...]], ...] = ()
    """Stored values a result may be restricted to, each with the words a
    question uses for it (T43). A closed set: without it, no filter."""

    def column_for(self, table: str) -> str | None:
        return dict(self.columns).get(table)

    def names(self) -> tuple[str, ...]:
        """The label and aliases, longest first so a regex prefers 来源渠道 to 渠道."""
        return tuple(sorted({self.label, *self.aliases}, key=len, reverse=True))

    def value_for(self, word: str) -> str | None:
        """The stored value a word names — the value itself or one of its words — or None."""
        for stored, words in self.values:
            if word == stored or word in words:
                return stored
        return None

    def value_words(self) -> tuple[str, ...]:
        """Every way a question may name one of the values, longest first."""
        every = {w for stored, words in self.values for w in (stored, *words)}
        return tuple(sorted(every, key=len, reverse=True))


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
# 「分」 is a split word only on its own: in 「部分」 or 「区分」 it is part of
# another word, and 「部分渠道」 is a subset, not a split. 「按日期」 is not
# 「按日」 either — it is as often which date attributes a record as how the
# result is split, so it is left to the undeclared-split check below.
_SPLIT_FEN = r"(?<![部区])分"
_TIME_PATTERNS = (
    (re.compile(rf"每一?天|每日|按天|按日(?!期)|逐日|{_SPLIT_FEN}天|{_SPLIT_FEN}日(?!期)"), DAY),
    (re.compile(rf"每一?周|每个?星期|按周|逐周|{_SPLIT_FEN}周"), WEEK),
    (re.compile(rf"每一?个?月|按月|逐月|{_SPLIT_FEN}月"), MONTH),
)
_SPLIT_WORDS = rf"(?:按|{_SPLIT_FEN}|各个|各|每一个|每个|不同)\s*"
# A split asked for by something no maintainer declared: 「各城市的」,
# 「每个用户的」, 「按城市分组」. Recognised only in these explicit shapes, and
# never where a declared dimension or a time grain already matched.
_UNDECLARED = re.compile(
    r"(?:(?<![部区])各个?(?![自位种类])|每一?个|不同的?)([一-鿿]{1,4}?)的"
    r"|按([一-鿿]{1,4}?)(?:分组|拆分|划分|分别|统计)"
)


def _dimension_pattern(dimension: Dimension) -> re.Pattern[str]:
    return re.compile(_SPLIT_WORDS + _alternation(dimension.names()))


def _alternation(words: tuple[str, ...]) -> str:
    return "(?:" + "|".join(re.escape(word) for word in words) + ")"


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
    taken = [(start, start + len(item.phrase)) for start, item in found]
    for match in _UNDECLARED.finditer(question):
        start, end = match.span()
        if any(start < right and left < end for left, right in taken):
            continue
        noun = match.group(1) or match.group(2)
        declared = "、".join(d.label for d in dimensions) or "无"
        raise GroupingError(
            f"问题像是要按「{noun}」分组，但维护者没有声明这个维度（已声明：{declared}）。"
            "可以按天 / 周 / 月或已声明的维度分组；要一个总数请写不分组。",
            undeclared=True,
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
    if text in (NONE, "不分组", "一个总数", "总数", "全部"):
        return NONE
    if text in (DAY, "天", "日", "每天", "每日", "按天", "按日"):
        return DAY
    if text in (WEEK, "周", "每周", "按周"):
        return WEEK
    if text in (MONTH, "月", "每月", "按月"):
        return MONTH
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


# ---------------------------------------------------------- value filters (T43)
#
# 「广告渠道的新增用户」 counts one value of a declared dimension. The value is
# bound, so it cannot inject anything; but a bound value nobody declared —
# 「抖音」 where the column holds ads / organic / referral — would match no
# rows and report 0 as if the business had done nothing. So values are a
# closed set a maintainer declares, and anything else is asked about.

FILTER_NONE = "none"
"""An explicit 「不过滤」: the rule is settled and nothing is filtered."""


class FilterError(AnswerError):
    """A restriction the question asks for that cannot become exactly one filter."""


@dataclass(frozen=True)
class FoundFilter:
    """A filter and the words in the question it was read from."""

    value: str
    phrase: str


def filter_value(dimension: Dimension, stored: str) -> str:
    """The canonical rule value: ``dim:channel=ads``."""
    return f"{DIMENSION_PREFIX}{dimension.key}={stored}"


def split_filter(value: str) -> tuple[str, str] | None:
    """``dim:channel=ads`` → ("channel", "ads"); None for no filter or anything malformed."""
    if not value.startswith(DIMENSION_PREFIX):
        return None
    key, sep, stored = value[len(DIMENSION_PREFIX) :].partition("=")
    if not sep or not stored or not _IDENTIFIER.fullmatch(key):
        return None
    return key, stored


def is_filter(value: str) -> bool:
    """True for a canonical rule value; anything else never reaches SQL."""
    return value == FILTER_NONE or split_filter(value) is not None


def filter_text(value: str, labels: Mapping[str, str] | None = None) -> str:
    """How a filter reads on the confirmation sheet."""
    parts = split_filter(value)
    if parts is None:
        return "不过滤（全部取值）"
    key, stored = parts
    return f"只统计「{(labels or {}).get(key, key)}」为 {stored} 的数据"


_JOINERS = r"(?:和|与|及|或|、|/)"
# A value word nobody declared must be a word of its own to be noticed: it
# starts after the start, punctuation, the end of a time phrase (「上个月」) or
# a split word (「各」), and contains none of them — otherwise 「上个月各渠道」
# reads as a value called 「上个月各」. Found in testing.
_BREAKS = r"\s，。、,；;：:的月天周年日在从自各按每"
_WORD_START = rf"(?:^|(?<=[{_BREAKS}]))"
_LONE_WORD = rf"[^{_BREAKS}]{{2,4}}"
_SPLIT_START = re.compile(r"^(?:按|分|各|每|不同)")
# 「渠道分布」「渠道占比」 ask about every value, not one.
_NOT_ONE_VALUE = r"(?!分布|占比|结构|构成|情况|对比|排名)"


def _undeclared_value(dimension: Dimension, word: str) -> FilterError:
    if not dimension.values:
        return FilterError(f"维护者没有为「{dimension.label}」声明取值，不能按它过滤。")
    options = "、".join(
        f"{words[0] if words else stored}（{stored}）" for stored, words in dimension.values
    )
    return FilterError(
        f"问题像是要只统计「{dimension.label}」为「{word}」的数据，但它不是维护者声明的取值"
        f"（可选：{options}）。要看每个取值请写「各{dimension.label}」。"
    )


def find_filter(
    question: str, dimensions: tuple[Dimension, ...] = (), *, ignore: tuple[str, ...] = ()
) -> FoundFilter | None:
    """The one declared value a question restricts the result to, or None.

    Two shapes: the value before the dimension's name (「广告渠道」) and after
    it (「渠道为广告」). ``ignore`` holds words that may stand before a
    dimension's name without naming a value — the metric's own name, as in
    「新增用户渠道」.

    Raises:
        FilterError: a value no maintainer declared (「抖音渠道」), several
            values (「广告和推荐渠道」), or restrictions on two dimensions.
    """
    found: dict[str, FoundFilter] = {}
    for dimension in dimensions:
        if not dimension.values:
            continue
        names = _alternation(dimension.names())
        words = _alternation(dimension.value_words())
        before = rf"({words}(?:{_JOINERS}{words})*){names}{_NOT_ONE_VALUE}"
        for match in re.finditer(before, question):
            picked = {dimension.value_for(word) for word in re.split(_JOINERS, match.group(1))}
            if len(picked) > 1:
                raise FilterError(
                    f"「{match.group(0)}」同时选了「{dimension.label}」的多个取值；一次只能按一个"
                    f"取值过滤，要看每个取值请写「各{dimension.label}」。"
                )
            value = filter_value(dimension, str(picked.pop()))
            found.setdefault(value, FoundFilter(value, match.group(0)))
        after = rf"{names}\s*(?:为|是|=|：|:)\s*(?:({words})|([^\s，。、,；;的]{{1,6}}))"
        for match in re.finditer(after, question):
            if not match.group(1):
                raise _undeclared_value(dimension, match.group(2))
            value = filter_value(dimension, str(dimension.value_for(match.group(1))))
            found.setdefault(value, FoundFilter(value, match.group(0)))
        unknown = rf"{_WORD_START}({_LONE_WORD}){names}{_NOT_ONE_VALUE}"
        for match in re.finditer(unknown, question):
            word, phrase = match.group(1), match.group(0)
            named = len(phrase) - len(word)
            if (
                dimension.value_for(word) is not None
                or _SPLIT_START.match(word)
                or any(term and term in word for term in ignore)
                # 「来源」 + 「渠道」 is the alias 「来源渠道」, not a value.
                or any(len(n) > named and phrase.endswith(n) for n in dimension.names())
            ):
                continue
            raise _undeclared_value(dimension, word)
    if len(found) > 1:
        phrases = "、".join(item.phrase for item in found.values())
        raise FilterError(
            f"问题里有多个过滤条件：{phrases}。一次只支持按一个维度的一个取值过滤。"
        )
    return next(iter(found.values()), None)


def parse_filter(text: str, dimensions: tuple[Dimension, ...] = ()) -> str:
    """A filter stated on purpose (``--filter`` or at a prompt): 渠道=广告, channel=ads,
    the same words a question would use, or none.

    Raises:
        FilterError: Nothing recognisable, an unknown dimension or an undeclared value.
    """
    text = text.strip()
    if text in (FILTER_NONE, "不过滤", "全部"):
        return FILTER_NONE
    for separator in ("=", "：", ":"):
        name, sep, word = text.partition(separator)
        if sep:
            name, word = name.strip(), word.strip()
            dimension = next((d for d in dimensions if name in (d.key, *d.names())), None)
            if dimension is None:
                declared = "、".join(d.label for d in dimensions if d.values) or "无"
                raise FilterError(f"没有名为「{name}」的可过滤维度（已声明取值的：{declared}）。")
            stored = dimension.value_for(word)
            if stored is None:
                raise _undeclared_value(dimension, word)
            return filter_value(dimension, stored)

    direct = []
    for dimension in dimensions:
        stored = dimension.value_for(text)
        if stored is not None:
            direct.append(filter_value(dimension, stored))
        for name in dimension.names():
            if text.endswith(name):
                prefix = text[: -len(name)].strip()
                for marker in ("只统计", "只看", "仅统计", "仅看"):
                    if prefix.startswith(marker):
                        prefix = prefix[len(marker) :].strip()
                stored = dimension.value_for(prefix)
                if stored is not None:
                    direct.append(filter_value(dimension, stored))
    if len(set(direct)) == 1:
        return direct[0]
    found = find_filter(text, dimensions)
    if found is None:
        raise FilterError(f"无法识别的过滤条件：{text!r}。可以写 渠道=广告；要全部数据写 none。")
    return found.value
