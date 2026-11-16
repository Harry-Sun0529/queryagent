"""What the terminal asks when a draft leaves something open.

``flow`` and ``confirm`` share these. Every answer becomes a rule through
``queryagent.workflow.answers``, the same reading the page and MCP use.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import date
from typing import TypeVar

from queryagent.errors import AnswerError
from queryagent.workflow.answers import (
    adopted_rule,
    implied_variant_rule,
    stated_filter,
    stated_grouping,
    stated_period,
    variant_rule,
)
from queryagent.workflow.builder import VARIANT_RULE_KEY
from queryagent.workflow.grouping import (
    Dimension,
    FilterError,
    GroupingError,
    find_filter,
    find_grouping,
)
from queryagent.workflow.models import (
    CONFLICT_SEPARATOR,
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    Candidate,
    DefinitionDraft,
    Rule,
    RuleSource,
)
from queryagent.workflow.periods import (
    PeriodAlternative,
    PeriodError,
    find_period,
    period_alternatives,
)
from queryagent.workflow.render import (
    rule_label,
)

_AnswerT = TypeVar("_AnswerT")

def _explain_missing_period(question: str, today: date) -> None:
    """Say why the question's own time words did not become a period."""
    try:
        find_period(question, today)
    except PeriodError as exc:
        print(f"[提示] {exc}", file=sys.stderr)


def _ask_until_valid(
    prompt: Callable[[], str],
    parse: Callable[[str], _AnswerT],
    *,
    max_attempts: int = 3,
) -> _AnswerT | None:
    """Read an answer, retrying parseable user mistakes without executing."""
    for _ in range(max_attempts):
        try:
            text = prompt()
        except EOFError:
            return None
        if not text:
            return None
        try:
            return parse(text)
        except AnswerError as exc:
            print(f"[无效] {exc}", file=sys.stderr)
    print("[已取消] 多次输入无法识别，没有执行任何查询。", file=sys.stderr)
    return None


def _prompt_period(question: str, today: date) -> str:
    choices = period_alternatives(question, today)
    if choices:
        print("\n这个时间表达有多种解释，请选择：")
        for index, choice in enumerate(choices, 1):
            print(f"  {index}) {choice.label}")
        prompt = "请输入编号，或写明确日期范围（回车取消）： "
    else:
        prompt = (
            "\n「统计区间」尚未确定。写下要统计的时间"
            "（如 上个月、2026-08-01..2026-08-31；回车取消）： "
        )
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _period_answer(text: str, question: str, today: date, source: RuleSource) -> Rule:
    choices = period_alternatives(question, today)
    if text.isdigit() and choices:
        index = int(text)
        if not 1 <= index <= len(choices):
            raise PeriodError(f"编号超出范围：请写 1 到 {len(choices)}")
        choice: PeriodAlternative = choices[index - 1]
        return Rule(
            PERIOD_RULE_KEY,
            choice.period.encode(),
            source,
            note=f"由「{question}」选择：{choice.label}",
        )
    return stated_period(text, today, source)


def _explain_missing_grouping(question: str, dimensions: tuple[Dimension, ...]) -> None:
    """Say why the question's own words did not become a grouping."""
    try:
        find_grouping(question, dimensions)
    except GroupingError as exc:
        print(f"[提示] {exc}", file=sys.stderr)


def _prompt_grouping() -> str:
    try:
        return input(
            "\n「分组方式」尚未确定。可写每天/每周/每月、day / week / month、维度名，"
            "要一个总数写不分组；回车取消）： "
        ).strip()
    except EOFError:
        return ""


def _explain_missing_filter(question: str, dimensions: tuple[Dimension, ...], name: str) -> None:
    """Say why the question's words did not become a filter."""
    try:
        find_filter(question, dimensions, ignore=(name,))
    except FilterError as exc:
        print(f"[提示] {exc}", file=sys.stderr)


def _prompt_filter() -> str:
    try:
        return input(
            "\n「取值过滤」尚未确定。可写 渠道=广告、广告渠道或 none；"
            "回车取消）： "
        ).strip()
    except EOFError:
        return ""


def _open_choices(
    draft: DefinitionDraft,
    args: argparse.Namespace,
    citations: dict[str, str],
    today: date,
    dimensions: tuple[Dimension, ...] = (),
    *,
    source: RuleSource,
) -> tuple[Rule, ...] | None:
    """The user's answer to every open choice, or None when they decline.

    ``source`` is the acting identity's ``authoring_source``: who a rule is
    marked as coming from is decided by who is at the door, not by this file.

    Document disagreements are asked first, then rules nothing has stated,
    then the executable variant: which handbook the user sides with, and what
    they take the gaps to mean, is what they need before picking what runs.
    The two answers are not checked against each other — the system cannot
    tell what a handbook sentence means — which is why the whole sheet is
    printed again before the final confirmation (D05).
    """
    definition = draft.definition
    disagreements = {
        key: [c for c in definition.candidates if c.rule_key == key]
        for key in definition.missing
        if key != VARIANT_RULE_KEY
    }
    disagreements = {key: options for key, options in disagreements.items() if options}
    valid = {c.key for options in disagreements.values() for c in options}
    unknown = [value for value in args.adopt if value not in valid]
    if unknown:
        raise ValueError(
            f"未知的文档取法：{', '.join(unknown)}；当前可采用："
            f"{', '.join(sorted(valid)) or '（没有文档分歧）'}"
        )
    gaps = [
        key for key in definition.missing if key != VARIANT_RULE_KEY and key not in disagreements
    ]
    supplied: dict[str, str] = {}
    for item in args.rule:
        key, sep, value = item.partition("=")
        if not sep or not value.strip():
            raise ValueError(
                f"--rule 需要写成 KEY=取值，例如 time_window=按自然月统计；收到：{item!r}"
            )
        supplied[key.strip()] = value.strip()
    stray = sorted(set(supplied) - set(gaps))
    if stray:
        raise ValueError(
            f"这些规则没有待补的缺口：{', '.join(stray)}；当前待补：{', '.join(gaps) or '（无）'}"
        )
    rules: list[Rule] = []
    for rule_key, options in disagreements.items():
        chosen_key = next(
            (value for value in args.adopt if value.split(CONFLICT_SEPARATOR, 1)[0] == rule_key),
            "",
        ) or _prompt_adopt(rule_label(rule_key), options)
        if not chosen_key:
            return None
        chosen = _resolve_adopt(rule_key, chosen_key, options)
        if chosen is None:
            return None
        # The words are the handbook's, the decision is the user's (D07): a
        # 本次约定 rule that keeps the adopted document's citation.
        rules.append(adopted_rule(definition, chosen.key, source))
    for key in gaps:
        if key == GROUP_RULE_KEY:
            if args.group_by or supplied.get(key):
                rules.append(
                    stated_grouping(
                        args.group_by or supplied[key], dimensions, source
                    )
                )
            else:
                rule = _ask_until_valid(
                    _prompt_grouping,
                    lambda text: stated_grouping(text, dimensions, source),
                )
                if rule is None:
                    return None
                rules.append(rule)
            continue
        if key == PERIOD_RULE_KEY:
            if args.period or supplied.get(key):
                rules.append(
                    _period_answer(args.period or supplied[key], args.question, today, source)
                )
            else:
                rule = _ask_until_valid(
                    lambda: _prompt_period(args.question, today),
                    lambda text: _period_answer(text, args.question, today, source),
                )
                if rule is None:
                    return None
                rules.append(rule)
            continue
        if key == FILTER_RULE_KEY:
            if args.value_filter or supplied.get(key):
                rules.append(
                    stated_filter(args.value_filter or supplied[key], dimensions, source)
                )
            else:
                rule = _ask_until_valid(
                    _prompt_filter,
                    lambda text: stated_filter(text, dimensions, source),
                )
                if rule is None:
                    return None
                rules.append(rule)
            continue
        # Nothing states this rule and nothing may default it: the user writes
        # it down, and it is marked as theirs (D07).
        value = supplied.get(key) or _prompt_rule(rule_label(key))
        if not value:
            return None
        rules.append(Rule(key, value, source))
    if VARIANT_RULE_KEY in definition.missing:
        implied = implied_variant_rule(definition, rules, source)
        if implied is not None and not args.variant:
            # The wording the user adopted names one executable reading; asking
            # them to pick again invites picking the other one (E13).
            rules.append(implied)
            return tuple(rules)
        rule = _ask_until_valid(
            lambda: _prompt_variant(draft),
            lambda text: _variant_answer(draft, text, source),
        )
        if rule is None:
            return None
        if implied is not None and rule.value != implied.value:
            raise ValueError(
                f"采用的文档写法对应口径 {implied.value}，--variant 却选了 {rule.value}；"
                "同一条命令里两者矛盾，请只保留一个"
            )
        rules.append(rule)
    return tuple(rules)


def _resolve_adopt(
    rule_key: str, chosen_key: str, options: list[Candidate]
) -> Candidate | None:
    """An adopted document reading, by internal key, by number, or by its words."""
    direct = next((c for c in options if c.key == chosen_key), None)
    if direct is not None:
        return direct
    stripped = chosen_key.strip()
    if stripped.isdigit():
        index = int(stripped)
        if 1 <= index <= len(options):
            return options[index - 1]
        print(f"[无效] 编号超出范围：请写 1 到 {len(options)}，或候选键。", file=sys.stderr)
        return None
    by_words = [
        c
        for c in options
        if chosen_key in (c.label, c.summary) or chosen_key == c.key
    ]
    if len(by_words) == 1:
        return by_words[0]
    print(
        f"[无效] 「{rule_label(rule_key)}」没有取法 '{chosen_key}'；"
        f"可选：{', '.join(c.key for c in options)} 或对应编号。",
        file=sys.stderr,
    )
    return None


def _variant_answer(draft: DefinitionDraft, choice: str, source: RuleSource) -> Rule:
    """A reading chosen at a prompt: canonical key, number, or its label."""
    definition = draft.definition
    options = [c for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY]
    direct = next((c for c in options if c.key == choice.strip()), None)
    if direct is not None:
        return variant_rule(definition, direct.key, source)
    stripped = choice.strip()
    if stripped.isdigit():
        index = int(stripped)
        if not 1 <= index <= len(options):
            from queryagent.errors import AnswerError as _AnswerError

            raise _AnswerError(f"编号超出范围：请写 1 到 {len(options)}")
        return variant_rule(definition, options[index - 1].key, source)
    by_label = [c for c in options if stripped in (c.label, c.summary)]
    if len(by_label) == 1:
        return variant_rule(definition, by_label[0].key, source)
    from queryagent.errors import AnswerError as _AnswerError

    raise _AnswerError(
        f"未听懂口径 '{choice}'；可选："
        f"{', '.join(c.key for c in options)} 或其编号。"
    )


def _prompt_rule(label: str) -> str:
    try:
        return input(f"\n「{label}」尚未写明，维护者要求写明。写下本次约定（回车取消）： ").strip()
    except EOFError:
        return ""


def _prompt_adopt(label: str, options: list[Candidate]) -> str:
    numbered = "，".join(
        f"{index}) {option.label or option.key}" for index, option in enumerate(options, 1)
    )
    keys = ", ".join(c.key for c in options)
    try:
        return input(
            f"\n「{label}」文档之间有分歧，采用哪一种写法（可输入编号、原文或 [{keys}]；"
            f"回车取消）：\n  {numbered}\n你的选择： "
        ).strip()
    except EOFError:
        return ""


def _prompt_variant(draft: DefinitionDraft) -> str:
    options = [
        c for c in draft.definition.candidates if c.rule_key == VARIANT_RULE_KEY
    ]
    numbered = "，".join(
        f"{index}) {option.label or option.key}" for index, option in enumerate(options, 1)
    )
    keys = ", ".join(c.key for c in options)
    try:
        return input(
            f"\n选择口径（可输入编号、名称或 [{keys}]；回车取消）：\n  {numbered}\n你的选择： "
        ).strip()
    except EOFError:
        return ""


def _prompt_confirm() -> bool:
    try:
        return input("\n确认按以上口径执行？[y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False
