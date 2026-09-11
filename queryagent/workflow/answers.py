"""Turning a typed answer into a rule: one reading for every door (T44/T45).

The terminal, the confirmation page and an agent over MCP all let someone
fill what a draft leaves open: pick a reading, adopt one side of a document
disagreement, state a period, a split, a filter, or a rule nothing states.
How each answer becomes a rule is decided here, once, so a period typed into
the page means what it means on the command line. What differs by door is
only the provenance, and the caller's identity decides that (ADR-013).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from queryagent.workflow.enforcement import consistent_variant
from queryagent.workflow.grouping import Dimension, parse_filter, parse_grouping
from queryagent.workflow.models import (
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    VARIANT_RULE_KEY,
    BusinessDefinition,
    Rule,
    RuleSource,
)
from queryagent.workflow.periods import parse_period

_OWN_FIELDS = (PERIOD_RULE_KEY, GROUP_RULE_KEY, FILTER_RULE_KEY, VARIANT_RULE_KEY)


@dataclass(frozen=True)
class Answers:
    """What one amendment says, before it is read. Empty fields say nothing."""

    variant: str = ""
    adopt: tuple[str, ...] = ()
    rules: tuple[tuple[str, str], ...] = ()
    period: str = ""
    group_by: str = ""
    value_filter: str = ""


def stated_period(text: str, today: date, source: RuleSource) -> Rule:
    """A period stated on purpose, parsed exactly as a question's would be.

    Raises PeriodError (a ValueError) when it cannot be read: a period that
    was typed but not understood must not quietly become no period at all.
    """
    period = parse_period(text, today)
    return Rule(PERIOD_RULE_KEY, period.encode(), source, note=f"由「{text}」换算")


def stated_grouping(text: str, dimensions: tuple[Dimension, ...], source: RuleSource) -> Rule:
    """A grouping stated on purpose. Raises GroupingError (a ValueError) when unreadable."""
    return Rule(GROUP_RULE_KEY, parse_grouping(text, dimensions), source, note=f"由「{text}」换算")


def stated_filter(text: str, dimensions: tuple[Dimension, ...], source: RuleSource) -> Rule:
    """A filter stated on purpose. Raises FilterError (a ValueError) when unreadable."""
    return Rule(FILTER_RULE_KEY, parse_filter(text, dimensions), source, note=f"由「{text}」换算")


def adopted_rule(definition: BusinessDefinition, key: str, source: RuleSource) -> Rule:
    """One side of a document disagreement, adopted.

    The words are the handbook's and the decision is the caller's (D07): a
    rule with the caller's provenance that keeps the adopted document's
    citation, so the sheet can still say where the wording came from.
    """
    candidate = definition.candidate(key)
    if candidate is None or candidate.rule_key == VARIANT_RULE_KEY:
        options = sorted(c.key for c in definition.candidates if c.rule_key != VARIANT_RULE_KEY)
        raise ValueError(
            f"未知的文档取法：{key}；当前可采用：{', '.join(options) or '（没有文档分歧）'}"
        )
    return Rule(
        candidate.rule_key,
        candidate.summary,
        source,
        evidence_ref=candidate.evidence_ref,
        note="采用文档写法",
        implies=candidate.implies,
    )


def variant_rule(definition: BusinessDefinition, key: str, source: RuleSource) -> Rule:
    """The executable reading chosen, saying what it overrides when it overrides something.

    A reading the documents or the caller's last confirmation picked stays on
    the sheet as what was overridden; choosing against it is allowed (E12).
    """
    variants = sorted(c.key for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY)
    if key not in variants:
        raise ValueError(f"未知口径 '{key}'；可选：{', '.join(variants)}")
    current = definition.rule(VARIANT_RULE_KEY)
    note = ""
    if current is not None and current.value != key:
        if current.source is RuleSource.HISTORY:
            note = "覆盖历史选择"
        elif current.source is RuleSource.DOC:
            note = "覆盖文档依据"
    return Rule(VARIANT_RULE_KEY, key, source, note=note)


def implied_variant_rule(
    definition: BusinessDefinition, adopted: list[Rule], source: RuleSource
) -> Rule | None:
    """The reading adopted wording names, when a reading is still open and it names one.

    Asking the caller to pick again after they adopted wording that names a
    reading invites picking the other one (E13).
    """
    if VARIANT_RULE_KEY not in definition.missing:
        return None
    variants = {c.key for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY}
    implied = consistent_variant([*definition.rules, *adopted], variants)
    if implied is None:
        return None
    reading, anchor = implied
    return Rule(
        VARIANT_RULE_KEY,
        reading,
        source,
        evidence_ref=anchor.evidence_ref,
        note="由采用的文档写法对应",
    )


def open_gaps(definition: BusinessDefinition) -> tuple[str, ...]:
    """Missing rules nothing but a typed value can fill: not a reading, not a disagreement."""
    disputed = {c.rule_key for c in definition.candidates}
    return tuple(
        key for key in definition.missing if key not in _OWN_FIELDS and key not in disputed
    )


def answer_rules(
    definition: BusinessDefinition,
    answers: Answers,
    *,
    source: RuleSource,
    today: date,
    dimensions: tuple[Dimension, ...] = (),
) -> tuple[Rule, ...]:
    """Every rule one amendment adds, read the same way whichever door it came through.

    Raises ValueError, naming what can be answered instead, for an answer
    that fits nothing on the draft. Whether the answers agree with each other
    — adopted wording against a chosen reading — is the service's to refuse,
    once, for every door.
    """
    rules = [adopted_rule(definition, key, source) for key in answers.adopt]
    gaps = open_gaps(definition)
    for key, value in answers.rules:
        if key in _OWN_FIELDS:
            raise ValueError(f"「{key}」有自己的字段，不能写成规则")
        if key not in gaps:
            raise ValueError(
                f"这些规则没有待补的缺口：{key}；当前待补：{', '.join(gaps) or '（无）'}"
            )
        if not value.strip():
            raise ValueError(f"规则 {key} 的取值不能为空")
        rules.append(Rule(key, value.strip(), source))
    if answers.period:
        rules.append(stated_period(answers.period, today, source))
    if answers.group_by:
        rules.append(stated_grouping(answers.group_by, dimensions, source))
    if answers.value_filter:
        rules.append(stated_filter(answers.value_filter, dimensions, source))
    if answers.variant:
        rules.append(variant_rule(definition, answers.variant, source))
    else:
        implied = implied_variant_rule(definition, rules, source)
        if implied is not None:
            rules.append(implied)
    if not rules:
        raise ValueError("这次补充没有内容：请给出口径、文档取法、区间、分组、过滤或缺口规则之一")
    return tuple(rules)
