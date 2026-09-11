"""Slice 1C-2: 「每天」「按渠道」 become one confirmable grouping, or a question (T38).

Parsing, the groups a period touches, and the draft rule. The SQL is in
test_query_compiler.py; the numbers per group in the end-to-end and
integration files.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from queryagent.metrics.base import Metric
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.grouping import (
    DAY,
    MONTH,
    NONE,
    WEEK,
    Dimension,
    GroupingError,
    bucket_starts,
    edges_are_partial,
    find_grouping,
    grouping_text,
    parse_grouping,
)
from queryagent.workflow.mappings import load_dimensions
from queryagent.workflow.models import (
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    BusinessDefinition,
    QueryRun,
    Rule,
    RuleSource,
    RunStatus,
)
from queryagent.workflow.periods import Period
from queryagent.workflow.render import render_rows

CHANNEL = Dimension("channel", "渠道", ("来源渠道",), (("users", "channel"),))
REGION = Dimension("region", "地区", ("区域",), (("users", "region"),))
DIMENSIONS = (CHANNEL, REGION)
AUGUST = Period(date(2026, 8, 1), date(2026, 8, 31))


@pytest.mark.parametrize(
    ("question", "value", "phrase"),
    [
        ("上个月每天的新增用户", DAY, "每天"),
        ("最近7天每日新增用户", DAY, "每日"),
        ("今年每周的成交额", WEEK, "每周"),
        ("今年每个月的成交额", MONTH, "每个月"),
        ("今年按月的成交额", MONTH, "按月"),
        ("上个月各渠道的新增用户", "dim:channel", "各渠道"),
        ("上个月按来源渠道的新增用户", "dim:channel", "按来源渠道"),
        ("上个月不同区域新增用户", "dim:region", "不同区域"),
    ],
)
def test_a_question_names_one_grouping(question: str, value: str, phrase: str) -> None:
    found = find_grouping(question, DIMENSIONS)
    assert found is not None
    assert (found.value, found.phrase) == (value, phrase)


@pytest.mark.parametrize(
    "question",
    ["上个月新增用户有多少？", "本月成交额", "8月的新增用户", "上个月（2026年8月）新增用户"],
)
def test_a_period_is_not_a_grouping(question: str) -> None:
    """「上个月」 names a range, not a split: the answer is still one number."""
    assert find_grouping(question, DIMENSIONS) is None


@pytest.mark.parametrize(
    "question",
    ["上个月日均新增用户", "上个月平均每天新增多少用户", "每天平均成交额", "今天每小时的新增用户"],
)
def test_an_average_or_an_unmade_split_is_refused_not_approximated(question: str) -> None:
    """E07: 「日均」 as 「每天」 is a table posing as an average; as nothing, a total."""
    with pytest.raises(GroupingError, match="不是这里能做的分组"):
        find_grouping(question, DIMENSIONS)


def test_two_different_groupings_are_refused() -> None:
    """E08: one split at a time."""
    with pytest.raises(GroupingError, match="多个不同的分组方式"):
        find_grouping("上个月每天各渠道的新增用户", DIMENSIONS)


def test_the_same_grouping_said_twice_is_one() -> None:
    found = find_grouping("按天统计，每天一行", DIMENSIONS)
    assert found is not None and found.value == DAY


@pytest.mark.parametrize(
    "question", ["上个月各城市的新增用户", "按城市分组的新增用户", "每个用户的成交额"]
)
def test_a_split_by_an_undeclared_dimension_is_asked_about_rather_than_totalled(
    question: str,
) -> None:
    """F9: a table was asked for; one total would silently answer something else."""
    with pytest.raises(GroupingError, match="没有声明这个维度"):
        find_grouping(question, DIMENSIONS)


@pytest.mark.parametrize(
    "question",
    ["上个月部分渠道的新增用户", "部分月份的成交额", "区分日期的新增用户", "上个月各自的新增用户"],
)
def test_words_that_merely_contain_a_split_word_are_not_a_split(question: str) -> None:
    """Found in review: 「部分」 is a subset and 「区分」 a verb, not 「分」 + a noun."""
    assert find_grouping(question, DIMENSIONS) is None


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("day", DAY),
        ("按天", DAY),
        ("每周", WEEK),
        ("month", MONTH),
        ("none", NONE),
        ("不分组", NONE),
        ("channel", "dim:channel"),
        ("渠道", "dim:channel"),
        ("区域", "dim:region"),
    ],
)
def test_a_stated_grouping_is_read_in_the_same_words(text: str, value: str) -> None:
    assert parse_grouping(text, DIMENSIONS) == value


def test_an_unrecognisable_stated_grouping_is_refused() -> None:
    with pytest.raises(GroupingError, match="无法识别的分组方式"):
        parse_grouping("按心情", DIMENSIONS)


def test_groupings_read_as_what_they_do() -> None:
    assert grouping_text(DAY) == "按天（每个日期一行）"
    assert grouping_text(NONE) == "不分组（一个总数）"
    assert grouping_text("dim:channel") == "按「channel」（每个取值一行）"
    # D04: with the maintainer's names at hand, the sheet says 渠道, not channel.
    assert grouping_text("dim:channel", {"channel": "渠道"}) == "按「渠道」（每个取值一行）"


# ------------------------------------------------------------------ groups


def test_weekly_groups_start_on_the_monday_before_the_period() -> None:
    assert bucket_starts(AUGUST, WEEK) == (
        date(2026, 7, 27),
        date(2026, 8, 3),
        date(2026, 8, 10),
        date(2026, 8, 17),
        date(2026, 8, 24),
        date(2026, 8, 31),
    )
    assert edges_are_partial(AUGUST, WEEK)


def test_the_months_a_period_touches_are_its_groups_and_partial_ones_are_flagged() -> None:
    summer = Period(date(2026, 7, 15), date(2026, 9, 10))
    assert bucket_starts(summer, MONTH) == (date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1))
    assert edges_are_partial(summer, MONTH)
    assert not edges_are_partial(AUGUST, MONTH)


def test_daily_groups_are_every_day_and_never_partial() -> None:
    assert len(bucket_starts(AUGUST, DAY)) == 31
    assert not edges_are_partial(AUGUST, DAY)


def test_a_period_of_whole_weeks_has_no_partial_edge() -> None:
    assert not edges_are_partial(Period(date(2026, 8, 31), date(2026, 9, 6)), WEEK)


# ------------------------------------------------------------------ draft


class _OneMetric:
    def __init__(self, metric: Metric) -> None:
        self._metric = metric

    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        return [self._metric]

    def get(self, name: str) -> Metric | None:
        return self._metric


def _build(question: str):  # type: ignore[no-untyped-def]
    metric = Metric(name="new_users", display_name="新增用户", definition="统计新加入的用户数。")
    builder = MetricDraftBuilder(
        _OneMetric(metric), today=lambda: date(2026, 9, 10), dimensions=DIMENSIONS
    )
    return builder.build(question)


def test_the_questions_grouping_is_the_users_rule_with_its_words() -> None:
    """F7: marked 本次约定 and naming the words it came from."""
    definition = _build("上个月各渠道的新增用户")
    rule = definition.rule(GROUP_RULE_KEY)
    assert rule is not None
    assert (rule.value, rule.source) == ("dim:channel", RuleSource.USER)
    assert "各渠道" in rule.note
    assert GROUP_RULE_KEY not in definition.missing


def test_an_average_leaves_the_grouping_to_be_asked() -> None:
    """F9: the question asked for something a total would not answer."""
    definition = _build("上个月日均新增用户")
    assert definition.rule(GROUP_RULE_KEY) is None
    assert GROUP_RULE_KEY in definition.missing


def test_no_grouping_words_leave_the_draft_as_it_was() -> None:
    definition = _build("上个月新增用户")
    assert definition.rule(GROUP_RULE_KEY) is None
    assert GROUP_RULE_KEY not in definition.missing


# ------------------------------------------------------------------ loading


def test_the_shipped_mappings_declare_channel_and_region_for_users() -> None:
    dimensions = load_dimensions("examples/query_mappings.yaml")
    assert {(d.key, d.column_for("users")) for d in dimensions} == {
        ("channel", "channel"),
        ("region", "region"),
    }
    assert all(d.column_for("orders") is None for d in dimensions)


@pytest.mark.parametrize(
    ("entry", "complaint"),
    [
        ("  - key: 'a b'\n    label: x\n    columns: {users: c}\n", "identifier"),
        ("  - key: a\n    label: 'x\"y'\n    columns: {users: c}\n", "quote"),
        ("  - key: a\n    label: x\n", "columns"),
        ("  - key: a\n    label: x\n    columns: {'users; DROP': c}\n", "table name"),
        ("  - key: a\n    label: x\n    columns: {users: 'c d'}\n", "column name"),
    ],
)
def test_malformed_dimensions_are_refused_at_load(
    tmp_path: Path, entry: str, complaint: str
) -> None:
    path = tmp_path / "m.yaml"
    path.write_text("dimensions:\n" + entry + "mappings: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match=complaint):
        load_dimensions(path)


def test_a_mappings_file_without_dimensions_declares_none(tmp_path: Path) -> None:
    path = tmp_path / "m.yaml"
    path.write_text("mappings: []\n", encoding="utf-8")
    assert load_dimensions(path) == ()


# ------------------------------------------------------------ filled result


def _daily_lines(rows: tuple[tuple[object, ...], ...], data_through: str) -> list[str]:
    definition = BusinessDefinition(
        "new_users",
        "新增用户",
        rules=(
            Rule(PERIOD_RULE_KEY, "2026-08-01..2026-08-05", RuleSource.USER),
            Rule(GROUP_RULE_KEY, DAY, RuleSource.USER),
        ),
    )
    run = QueryRun(
        "r", "d", "c", "alice", "k", RunStatus.SUCCEEDED,
        columns=("日期", "n"),
        rows=rows,
        freshness_sql="SELECT MAX(created_at) FROM users",
        data_through=data_through,
    )  # fmt: skip
    return render_rows(definition, run)


def test_an_empty_day_inside_the_data_reads_no_records_and_after_it_no_data() -> None:
    """F8: the two absences are different claims, and each day gets its own line."""
    lines = _daily_lines((("2026-08-01", 5), ("2026-08-03", 2)), "2026-08-03")
    assert lines[1:] == [
        "  2026-08-01 | 5",
        "  2026-08-02 | （无记录）",
        "  2026-08-03 | 2",
        "  2026-08-04 | （无数据）",
        "  2026-08-05 | （无数据）",
    ]


def test_when_the_datas_reach_is_unknown_an_empty_day_is_called_neither() -> None:
    """Found in review: a failed probe must not turn 无数据 into 无记录 (F5)."""
    lines = _daily_lines((("2026-08-01", 5),), "")
    assert lines[2:] == [f"  2026-08-0{day} | （未知：无记录或尚无数据）" for day in (2, 3, 4, 5)]
