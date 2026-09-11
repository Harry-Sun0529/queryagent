"""Slice 1D/1E: 「广告渠道的新增用户」 counts one declared value, bound (T43).

Parsing, the draft rule, loading and the SQL here, plus one run on SQLite
against a count in Python. The numbers against each server dialect's own
WHERE are in the integration files.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from queryagent.cli import main
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.metrics.base import Metric
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import TemplateCompiler
from queryagent.workflow.errors import MappingNotFound, WorkflowStateError
from queryagent.workflow.grouping import (
    FILTER_NONE,
    Dimension,
    FilterError,
    filter_text,
    find_filter,
    parse_filter,
)
from queryagent.workflow.mappings import QueryMapping, load_dimensions
from queryagent.workflow.models import (
    ALLOWED_RULE_KEYS,
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    VARIANT_RULE_KEY,
    BusinessDefinition,
    Rule,
    RuleSource,
)

CHANNEL = Dimension(
    "channel",
    "渠道",
    ("来源渠道",),
    (("users", "channel"),),
    values=(
        ("ads", ("广告", "付费投放")),
        ("organic", ("自然流量",)),
        ("referral", ("推荐", "邀请")),
    ),
)
REGION = Dimension(
    "region",
    "地区",
    ("区域",),
    (("users", "region"),),
    values=(("east", ("华东",)), ("overseas", ("海外",))),
)
DIMENSIONS = (CHANNEL, REGION)
NAMES = ("新增用户",)


# ------------------------------------------------------------------ parsing


@pytest.mark.parametrize(
    ("question", "value", "phrase"),
    [
        ("上个月广告渠道的新增用户", "dim:channel=ads", "广告渠道"),
        ("上个月付费投放渠道新增多少用户", "dim:channel=ads", "付费投放渠道"),
        ("渠道为推荐的新增用户", "dim:channel=referral", "渠道为推荐"),
        ("上个月华东地区的新增用户", "dim:region=east", "华东地区"),
        ("区域是海外的新增用户", "dim:region=overseas", "区域是海外"),
        ("ads渠道的新增用户", "dim:channel=ads", "ads渠道"),
    ],
)
def test_a_question_names_one_declared_value(question: str, value: str, phrase: str) -> None:
    found = find_filter(question, DIMENSIONS, ignore=NAMES)
    assert found is not None
    assert (found.value, found.phrase) == (value, phrase)


@pytest.mark.parametrize(
    "question",
    [
        "上个月各渠道的新增用户",
        "看看各渠道的新增用户",
        "上个月不同渠道的新增用户",
        "按来源渠道的新增用户",
        "上个月新增用户",
        "广告费是多少",
        "推荐语的点击量",
        "新增用户渠道分布",
        "上个月新增用户渠道占比",
        "上个月新增用户渠道",
    ],
)
def test_a_split_a_share_or_a_lookalike_word_is_not_a_filter(question: str) -> None:
    """「各渠道」 splits, 「渠道分布」 asks about every value, 「广告费」 is another word."""
    assert find_filter(question, DIMENSIONS, ignore=NAMES) is None


@pytest.mark.parametrize("question", ["上个月抖音渠道的新增用户", "渠道为抖音的新增用户"])
def test_a_value_nobody_declared_is_asked_about_with_the_options(question: str) -> None:
    """G18: bound as a parameter it would match nothing and read as 0."""
    with pytest.raises(
        FilterError, match="「抖音」.*可选：广告（ads）、自然流量（organic）、推荐（referral）"
    ):
        find_filter(question, DIMENSIONS, ignore=NAMES)


def test_two_values_or_two_dimensions_are_refused() -> None:
    with pytest.raises(FilterError, match="多个取值"):
        find_filter("广告和推荐渠道的新增用户", DIMENSIONS)
    with pytest.raises(FilterError, match="多个过滤条件"):
        find_filter("华东地区广告渠道的新增用户", DIMENSIONS)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("渠道=广告", "dim:channel=ads"),
        ("channel=ads", "dim:channel=ads"),
        ("地区：华东", "dim:region=east"),
        ("华东地区", "dim:region=east"),
        ("none", FILTER_NONE),
        ("不过滤", FILTER_NONE),
    ],
)
def test_a_stated_filter_is_read_in_the_same_words(text: str, value: str) -> None:
    assert parse_filter(text, DIMENSIONS) == value


@pytest.mark.parametrize(
    ("text", "complaint"),
    [
        ("城市=北京", "没有名为「城市」"),
        ("渠道=抖音", "不是维护者声明的取值"),
        ("随便", "无法识别"),
    ],
)
def test_an_unreadable_stated_filter_is_refused(text: str, complaint: str) -> None:
    with pytest.raises(FilterError, match=complaint):
        parse_filter(text, DIMENSIONS)


def test_a_filter_reads_as_what_it_counts() -> None:
    assert filter_text("dim:channel=ads", {"channel": "渠道"}) == "只统计「渠道」为 ads 的数据"
    assert filter_text(FILTER_NONE) == "不过滤（全部取值）"


# -------------------------------------------------------------------- draft


def _definition(question: str) -> BusinessDefinition:
    metric = Metric(name="new_users", display_name="新增用户", definition="统计新加入的用户数。")

    class _One:
        def match(self, question: str, top_k: int = 3) -> list[Metric]:
            return [metric]

        def get(self, name: str) -> Metric | None:
            return metric

    return MetricDraftBuilder(_One(), dimensions=DIMENSIONS).build(question)


def test_the_questions_filter_is_the_users_rule_with_its_words() -> None:
    """Like the period and the split: 本次约定, naming the words it came from."""
    rule = _definition("上个月广告渠道的新增用户").rule(FILTER_RULE_KEY)
    assert rule is not None
    assert (rule.value, rule.source) == ("dim:channel=ads", RuleSource.USER)
    assert "广告渠道" in rule.note


def test_an_undeclared_value_leaves_the_filter_to_be_asked() -> None:
    definition = _definition("上个月抖音渠道的新增用户")
    assert definition.rule(FILTER_RULE_KEY) is None
    assert FILTER_RULE_KEY in definition.missing


def test_documents_cannot_restrict_what_a_number_counts() -> None:
    """G18: the extraction pipeline only fills keys in this set."""
    assert FILTER_RULE_KEY not in ALLOWED_RULE_KEYS


# ------------------------------------------------------------------ compile

USERS = QueryMapping("users", "COUNT(*)", "n", "created_at", ("channel <> 'internal_test'",))


def _rules(*extra: Rule) -> BusinessDefinition:
    return BusinessDefinition(
        "new_users",
        "新增用户",
        rules=(
            Rule(VARIANT_RULE_KEY, "registered", RuleSource.USER),
            Rule(PERIOD_RULE_KEY, "2026-08-01..2026-08-31", RuleSource.USER),
            *extra,
        ),
    )


ADS = Rule(FILTER_RULE_KEY, "dim:channel=ads", RuleSource.USER)


def _compile(definition: BusinessDefinition, mapping: QueryMapping | str = USERS) -> object:
    compiler = TemplateCompiler({("new_users", "registered"): mapping}, dimensions=DIMENSIONS)
    return compiler.compile(definition)


def test_the_value_is_bound_after_the_period_not_written_into_the_statement() -> None:
    """G17: the statement holds a placeholder; the value travels beside it."""
    query = _compile(_rules(ADS))
    assert query.sql == (  # type: ignore[attr-defined]
        "SELECT COUNT(*) AS \"n\" FROM users WHERE (channel <> 'internal_test') "
        "AND created_at >= ? AND created_at < ? AND channel = ?"
    )
    assert query.params == ("2026-08-01", "2026-09-01", "ads")  # type: ignore[attr-defined]


def test_a_filter_and_a_split_compile_together() -> None:
    query = _compile(_rules(ADS, Rule(GROUP_RULE_KEY, "day", RuleSource.USER)))
    assert "channel = ? GROUP BY" in query.sql  # type: ignore[attr-defined]
    assert query.params[-1] == "ads"  # type: ignore[attr-defined]


def test_no_filter_adds_no_condition() -> None:
    query = _compile(_rules(Rule(FILTER_RULE_KEY, FILTER_NONE, RuleSource.USER)))
    assert "channel = ?" not in query.sql  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("mapping", "rule", "error", "complaint"),
    [
        (
            QueryMapping("orders", "SUM(amount)", "gmv", "created_at"),
            ADS,
            MappingNotFound,
            "无法按它过滤",
        ),
        (USERS, Rule(FILTER_RULE_KEY, "dim:channel=douyin", RuleSource.USER),
         WorkflowStateError, "没有声明取值"),
        (USERS, Rule(FILTER_RULE_KEY, "dim:channel", RuleSource.USER),
         WorkflowStateError, "不是规范值"),
        ("SELECT COUNT(*) FROM users", ADS, MappingNotFound, "无法按已确认的取值过滤"),
    ],
)  # fmt: skip
def test_a_filter_that_cannot_apply_is_refused_rather_than_dropped(
    mapping: QueryMapping | str, rule: Rule, error: type[Exception], complaint: str
) -> None:
    """A table without the dimension, a value nobody declared, a malformed rule,
    a whole statement: each would otherwise count every value under a filtered 口径."""
    definition = _rules(rule)
    if isinstance(mapping, str):
        variant = Rule(VARIANT_RULE_KEY, "registered", RuleSource.USER)
        definition = BusinessDefinition("new_users", "新增用户", rules=(variant, rule))
    with pytest.raises(error, match=complaint):
        _compile(definition, mapping)


def test_on_sqlite_the_filtered_count_is_the_count_python_makes(tmp_path: Path) -> None:
    rows = [
        ("ads", "2026-08-03"), ("ads", "2026-08-31 23:00:00"), ("organic", "2026-08-10"),
        ("ads", "2026-09-01"), ("internal_test", "2026-08-05"), ("ads", "2026-07-31"),
    ]  # fmt: skip
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE users (channel TEXT, created_at TEXT)")
    connection.executemany("INSERT INTO users VALUES (?,?)", rows)
    connection.commit()
    connection.close()
    total = _compile(_rules(ADS))
    daily = _compile(_rules(ADS, Rule(GROUP_RULE_KEY, "day", RuleSource.USER)))
    connector = SQLiteConnector(path=str(tmp_path / "shop.db"))
    result = connector.execute(total.sql, timeout_s=5, max_rows=10, params=total.params)  # type: ignore[attr-defined]
    by_day = connector.execute(daily.sql, timeout_s=5, max_rows=10, params=daily.params)  # type: ignore[attr-defined]
    connector.close()
    expected = sum(
        1 for channel, at in rows if channel == "ads" and "2026-08-01" <= at[:10] <= "2026-08-31"
    )
    assert result.rows == ((expected,),) == ((2,),)
    # G17: split by day as well, the groups add up to the same total.
    assert sum(row[1] for row in by_day.rows) == expected


# ------------------------------------------------------------------ loading


def test_the_shipped_mappings_declare_values_for_channel_and_region() -> None:
    dimensions = {d.key: d for d in load_dimensions("examples/query_mappings.yaml")}
    assert dimensions["channel"].value_for("广告") == "ads"
    assert dimensions["region"].value_for("华东") == "east"


@pytest.mark.parametrize(
    ("values", "complaint"),
    [
        ("[ads]", "map each stored value"),
        ("{ads: 广告}", "list of non-empty words"),
        ("{ads: [推广], referral: [推广]}", "names two values"),
    ],
)
def test_malformed_values_are_refused_at_load(
    tmp_path: Path, values: str, complaint: str
) -> None:
    path = tmp_path / "m.yaml"
    path.write_text(
        "dimensions:\n  - key: channel\n    label: 渠道\n    columns: {users: channel}\n"
        f"    values: {values}\nmappings: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=complaint):
        load_dimensions(path)


# ---------------------------------------------------------------------- CLI

CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: {db}
metrics_path: {metrics}
workflow:
  mappings_path: {mappings}
  state_path: {state}
trace: false
"""

MAPPINGS_YAML = """\
dimensions:
  - key: channel
    label: 渠道
    columns: {users: channel}
    values:
      ads: [广告]
      organic: [自然流量]
mappings:
  - metric: new_users
    from: users
    measure: COUNT(*)
    label: n
    time_column: created_at
"""


@pytest.fixture
def config(tmp_path: Path) -> Path:
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE users (channel TEXT, created_at TEXT)")
    connection.executemany(
        "INSERT INTO users VALUES (?,?)",
        [("ads", "2026-08-03"), ("ads", "2026-08-04"), ("organic", "2026-08-05")],
    )
    connection.commit()
    connection.close()
    (tmp_path / "metrics.yaml").write_text(
        "metrics:\n  - name: new_users\n    display_name: 新增用户\n    definition: 新用户数。\n",
        encoding="utf-8",
    )
    (tmp_path / "mappings.yaml").write_text(MAPPINGS_YAML, encoding="utf-8")
    path = tmp_path / "config.yaml"
    path.write_text(
        CONFIG.format(
            db=tmp_path / "shop.db",
            metrics=tmp_path / "metrics.yaml",
            mappings=tmp_path / "mappings.yaml",
            state=tmp_path / "workflow.db",
        ),
        encoding="utf-8",
    )
    return path


def test_the_flow_counts_only_the_stated_value(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["flow", "新增用户有多少？", "--config", str(config), "--period",
         "2026-08-01..2026-08-31", "--filter", "渠道=广告", "--yes"]
    )  # fmt: skip
    assert code == 0
    out = capsys.readouterr().out
    assert "只统计「渠道」为 ads 的数据" in out
    assert out.split("结果（")[1].splitlines()[2].strip() == "2"
    assert "参数（按 ? 的顺序绑定）：2026-08-01, 2026-09-01, ads" in out


def test_an_undeclared_value_in_the_question_stops_before_any_query(
    config: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    code = main(
        ["flow", "抖音渠道的新增用户有多少？", "--config", str(config), "--period",
         "2026-08-01..2026-08-31", "--yes"]
    )  # fmt: skip
    assert code == 2
    assert "不是维护者声明的取值" in capsys.readouterr().err
    state = sqlite3.connect(config.parent / "workflow.db")
    assert state.execute("SELECT COUNT(*) FROM runs").fetchone() == (0,)
    state.close()
