"""v1.0 T44/T45: a typed answer becomes the same rule whichever door it came through."""

from __future__ import annotations

from datetime import date

import pytest

from queryagent.workflow.answers import Answers, answer_rules, variant_rule
from queryagent.workflow.grouping import Dimension
from queryagent.workflow.models import (
    VARIANT_RULE_KEY,
    BusinessDefinition,
    Candidate,
    Rule,
    RuleSource,
)

TODAY = date(2026, 9, 10)
CHANNEL = Dimension(
    key="channel",
    label="渠道",
    columns=(("users", "channel"),),
    values=(("ads", ("广告",)), ("organic", ("自然流量",))),
)

OPEN = BusinessDefinition(
    metric="new_users",
    display_name="新增用户",
    missing=(VARIANT_RULE_KEY, "counting_basis", "time_window"),
    candidates=(
        Candidate("registered", "注册口径", "按注册日期"),
        Candidate("first_order", "首单口径", "按首单日期"),
        Candidate("counting_basis:0", "运营手册", "按注册日期计数", "d1#c1@0:9", ("registered",)),
        Candidate("counting_basis:1", "增长周报", "按首单日期计数", "d2#c1@0:9", ("first_order",)),
    ),
)


def _answer(answers: Answers, source: RuleSource = RuleSource.AGENT) -> tuple[Rule, ...]:
    return answer_rules(OPEN, answers, source=source, today=TODAY, dimensions=(CHANNEL,))


def test_every_rule_carries_the_callers_provenance() -> None:
    rules = _answer(Answers(variant="registered", period="上个月", value_filter="渠道=广告"))
    assert {rule.source for rule in rules} == {RuleSource.AGENT}
    assert {rule.key: rule.value for rule in rules} == {
        "period": "2026-08-01..2026-08-31",
        "filter": "dim:channel=ads",
        "variant": "registered",
    }


def test_adopted_wording_keeps_its_citation_and_names_the_reading_it_implies() -> None:
    """E13 for every door: adopting a handbook that names a reading settles the reading."""
    rules = _answer(Answers(adopt=("counting_basis:1",)))
    adopted, implied = rules
    assert (adopted.key, adopted.evidence_ref, adopted.note) == (
        "counting_basis",
        "d2#c1@0:9",
        "采用文档写法",
    )
    assert (implied.key, implied.value, implied.note) == (
        VARIANT_RULE_KEY,
        "first_order",
        "由采用的文档写法对应",
    )


def test_a_gap_nothing_states_is_filled_as_written() -> None:
    (rule,) = _answer(Answers(rules=(("time_window", " 按自然月 "),)), RuleSource.USER)
    assert (rule.key, rule.value, rule.source) == ("time_window", "按自然月", RuleSource.USER)


def test_answers_that_fit_nothing_on_the_draft_are_refused_with_what_would() -> None:
    with pytest.raises(ValueError, match="当前可采用：counting_basis:0, counting_basis:1"):
        _answer(Answers(adopt=("registered",)))
    with pytest.raises(ValueError, match="当前待补：time_window"):
        _answer(Answers(rules=(("dedup", "按用户"),)))
    with pytest.raises(ValueError, match="有自己的字段"):
        _answer(Answers(rules=(("period", "上个月"),)))
    with pytest.raises(ValueError, match="可选：first_order, registered"):
        _answer(Answers(variant="whatever"))
    with pytest.raises(ValueError, match="没有内容"):
        _answer(Answers())


def test_choosing_against_the_documents_or_history_says_so() -> None:
    """E12: the override stays visible on the sheet."""
    for source, note in ((RuleSource.DOC, "覆盖文档依据"), (RuleSource.HISTORY, "覆盖历史选择")):
        chosen = Rule(
            VARIANT_RULE_KEY, "registered", source, evidence_ref="d#c@0:1", note="沿用"
        )
        definition = BusinessDefinition(
            metric="new_users",
            display_name="新增用户",
            rules=(chosen,),
            candidates=OPEN.candidates,
        )
        assert variant_rule(definition, "first_order", RuleSource.USER).note == note
        assert variant_rule(definition, "registered", RuleSource.USER).note == ""
