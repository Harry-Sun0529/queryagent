"""Rendering a draft 口径 for a human to approve.

Deliberately business-first (D04): the reader is a PM or an operator who has
to be able to repeat this definition to a colleague. Rules come first with
where each one came from; the SQL is a detail shown after the decision, not
the thing being approved.

The provenance marks are the point. 「文档依据」/「本次约定」/「系统映射」 is
the distinction the whole product exists to make legible, and it must never
be collapsed into an unattributed paragraph.
"""

from __future__ import annotations

from queryagent.workflow.builder import VARIANT_RULE_KEY
from queryagent.workflow.models import (
    COMPILED_RULE_KEYS,
    PERIOD_RULE_KEY,
    BusinessDefinition,
    Candidate,
    DefinitionDraft,
    Rule,
    RuleSource,
)
from queryagent.workflow.periods import Period

_SOURCE_LABELS = {
    RuleSource.DOC: "文档依据",
    RuleSource.USER: "本次约定",
    RuleSource.MAINTAINER: "系统映射",
}

_RULE_LABELS = {
    "metric": "统计对象",
    "definition": "指标说明",
    "tables": "涉及数据表",
    "variant": "选定口径",
    "period": "统计区间",
    # Extracted rule keys. A confirmation sheet whose field names are English
    # identifiers is not something an operator can repeat to a colleague,
    # which is the whole acceptance test for this screen (D04).
    "counting_basis": "统计口径",
    "filters": "过滤条件",
    "time_window": "统计周期",
    "dedup": "去重方式",
    "refund_handling": "退款处理",
    "amount_basis": "金额口径",
}


def _location(citations: dict[str, str] | None, evidence_ref: str) -> str:
    """Look a citation's location up, ignoring the quote span.

    The stored ref pins the exact quote offsets; the retrieval result that
    knows the file and line does not. Keying on document and chunk is what
    makes the two meet — matching on the full string silently found nothing
    and the sheet showed rules with no source, which is precisely the
    unattributed summary this layer exists to avoid.
    """
    if not citations or not evidence_ref:
        return ""
    return citations.get(evidence_ref.split("@")[0], "")


def rule_label(key: str) -> str:
    """The operator-facing name of a rule key."""
    return _RULE_LABELS.get(key, key)


def _candidate_lines(candidates: list[Candidate], citations: dict[str, str] | None) -> list[str]:
    lines = []
    for candidate in candidates:
        summary = f" — {candidate.summary}" if candidate.summary != candidate.label else ""
        lines.append(f"  [{candidate.key}] {candidate.label}{summary}")
        where = _location(citations, candidate.evidence_ref)
        if where:
            lines.append(f"      出处：{where}")
    return lines


def _rule_text(definition: BusinessDefinition, rule: Rule) -> str:
    """Render a rule's value for a human.

    A variant rule's value is a lookup key — meaningful to the compiler,
    meaningless to the operator who has to repeat this 口径 to a colleague.
    Show the maintainer's own wording instead (D04).
    """
    if rule.key == PERIOD_RULE_KEY:
        try:
            text = Period.decode(rule.value).render()
        except ValueError:
            return rule.value
        return f"{text}（{rule.note}）" if rule.note else text
    if rule.key == VARIANT_RULE_KEY:
        candidate = definition.candidate(rule.value)
        if candidate is not None:
            return f"{candidate.label} — {candidate.summary}"
    return rule.value


def render_draft(
    draft: DefinitionDraft, citations: dict[str, str] | None = None
) -> str:
    """Render the confirmation sheet shown before anything is executed.

    ``citations`` maps a rule's ``evidence_ref`` to a human-readable location
    — file, section, line. A summary without one is an assertion, not
    evidence: the reader has to be able to open the document and check
    (D01). Omitted for maintainer-only drafts, which cite nothing.
    """
    definition = draft.definition
    lines = [
        f"口径确认单  #{draft.draft_id[:8]}  v{draft.version}",
        f"问题：{draft.question}",
        "",
        f"指标：{definition.display_name}",
    ]
    for rule in definition.rules:
        label = _RULE_LABELS.get(rule.key, rule.key)
        mark = _SOURCE_LABELS[rule.source]
        lines.append(f"  · {label}：{_rule_text(definition, rule)}    [{mark}]")
        where = _location(citations, rule.evidence_ref)
        if where:
            lines.append(f"      出处：{where}")
    variants = [c for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY]
    disagreements: dict[str, list[Candidate]] = {}
    for candidate in definition.candidates:
        if candidate.rule_key != VARIANT_RULE_KEY:
            disagreements.setdefault(candidate.rule_key, []).append(candidate)
    if variants:
        lines.extend(["", "可选口径（维护者定义的可执行取法，需要你选一个）："])
        lines.extend(_candidate_lines(variants, citations))
    for rule_key, options in disagreements.items():
        # Once adopted, the choice is a 本次约定 rule above, with its source;
        # the options stay listed so the rejected reading is not hidden.
        state = (
            "需要你采用其中一种写法"
            if rule_key in definition.missing
            else "已采用其中一种，见上方「本次约定」"
        )
        lines.extend(["", f"文档之间的分歧 · {rule_label(rule_key)}（{state}）："])
        lines.extend(_candidate_lines(options, citations))
    if definition.missing:
        missing = "、".join(_RULE_LABELS.get(key, key) for key in definition.missing)
        lines.extend(["", f"尚未确定：{missing}（确定前不会执行任何查询）"])
    lines.extend(["", f"内容指纹：{draft.definition_hash[:16]}"])
    return "\n".join(lines)


def render_definition_summary(definition: BusinessDefinition) -> str:
    """One-line recap attached to a result: the reading the number came from.

    Only what the executed query applied — the maintainer-declared variant
    and the confirmed period.
    Document rules and 本次约定 explain the 口径, but the compiler does not
    consume them, so listing them here would claim the number honours a rule
    (a monthly window, say) that the SQL does not implement. It did claim
    exactly that until a live run showed 「统计周期=按自然月」 above an
    all-time COUNT.
    """
    parts = [definition.display_name]
    parts.extend(
        f"{rule_label(rule.key)}={_rule_text(definition, rule)}"
        for rule in definition.rules
        if rule.key in COMPILED_RULE_KEYS
    )
    if definition.rule(PERIOD_RULE_KEY) is None:
        # Said out loud (P9): no window is a fact about this number, not a
        # default the reader should have to work out from the SQL.
        parts.append(f"{rule_label(PERIOD_RULE_KEY)}=未限定（全部数据）")
    return "；".join(parts)


def render_unenforced(definition: BusinessDefinition) -> str:
    """Name the confirmed rules the executed query did not itself apply, or ''.

    The system cannot tell whether a maintainer's SQL happens to implement a
    handbook sentence, so it says so rather than implying either way.
    """
    labels = [
        rule_label(rule.key)
        for rule in definition.rules
        if rule.source is not RuleSource.MAINTAINER and rule.key not in COMPILED_RULE_KEYS
    ]
    if not labels:
        return ""
    return (
        f"说明：{'、'.join(labels)} 来自文档或本次约定，用于解释口径；本次执行的是"
        "维护者映射（见下方 SQL），系统不核对两者是否一致。"
    )
