"""Regression tests for human-friendly flow answers and retry behavior."""

from __future__ import annotations

from datetime import date

import pytest

from queryagent.cli import _ask_until_valid, _explain
from queryagent.errors import AnswerError
from queryagent.workflow.grouping import Dimension, parse_filter, parse_grouping
from queryagent.workflow.periods import period_alternatives

TODAY = date(2026, 9, 10)
DIMENSIONS = (
    Dimension(
        "channel",
        "渠道",
        ("来源渠道",),
        (("users", "channel"),),
        values=(("ads", ("广告", "付费投放")), ("organic", ("自然流量",))),
    ),
)


def test_invalid_answer_is_classified_as_user_input_not_config() -> None:
    problem, fix, code = _explain(AnswerError("无法识别这次输入"))

    assert code == 2
    assert "配置" not in problem
    assert "config.yaml" not in fix


def test_prompt_retries_after_invalid_answer_and_returns_parsed_value(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["y", "按天"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    result = _ask_until_valid(
        lambda: input("分组：").strip(),
        lambda text: parse_grouping(text),
    )

    assert result == "day"
    assert "[无效]" in capsys.readouterr().err


def test_three_invalid_answers_cancel_without_hanging(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["y", "maybe", "???"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    result = _ask_until_valid(
        lambda: input("过滤：").strip(),
        lambda text: parse_filter(text, DIMENSIONS),
    )

    assert result is None


def test_grouping_accepts_human_aliases() -> None:
    assert parse_grouping("每天") == "day"
    assert parse_grouping("按周") == "week"
    assert parse_grouping("每月") == "month"
    assert parse_grouping("一个总数") == "none"


def test_filter_accepts_a_declared_value_without_internal_syntax() -> None:
    assert parse_filter("广告", DIMENSIONS) == "dim:channel=ads"
    assert parse_filter("只看广告渠道", DIMENSIONS) == "dim:channel=ads"


def test_near_two_months_exposes_choices_instead_of_picking_silently() -> None:
    choices = period_alternatives("近两个月新增用户", TODAY)

    assert len(choices) >= 2
    assert all(choice.period.start <= choice.period.end for choice in choices)
    assert len({choice.period for choice in choices}) == len(choices)
    assert all(choice.label for choice in choices)
