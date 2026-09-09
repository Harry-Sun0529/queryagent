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
from queryagent.workflow.models import BusinessDefinition, DefinitionDraft, Rule, RuleSource

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


def _rule_text(definition: BusinessDefinition, rule: Rule) -> str:
    """Render a rule's value for a human.

    A variant rule's value is a lookup key — meaningful to the compiler,
    meaningless to the operator who has to repeat this 口径 to a colleague.
    Show the maintainer's own wording instead (D04).
    """
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
    if definition.candidates:
        lines.extend(["", "可选口径（文档/维护者存在不同取法，需要你选一个）："])
        for candidate in definition.candidates:
            summary = f" — {candidate.summary}" if candidate.summary != candidate.label else ""
            lines.append(f"  [{candidate.key}] {candidate.label}{summary}")
            where = _location(citations, candidate.evidence_ref)
            if where:
                lines.append(f"      出处：{where}")
    if definition.missing:
        missing = "、".join(_RULE_LABELS.get(key, key) for key in definition.missing)
        lines.extend(["", f"尚未确定：{missing}（确定前不会执行任何查询）"])
    lines.extend(["", f"内容指纹：{draft.definition_hash[:16]}"])
    return "\n".join(lines)


# Background prose belongs on the confirmation sheet, where the user is
# deciding. A result recap has a different job: name the reading this number
# was produced under, briefly enough to be repeated out loud.
_RECAP_SKIP = ("metric", "tables", "definition")


def render_definition_summary(definition: BusinessDefinition) -> str:
    """One-line recap attached to a result, so a number never travels alone."""
    parts = [definition.display_name]
    parts.extend(
        f"{_RULE_LABELS.get(rule.key, rule.key)}={_rule_text(definition, rule)}"
        for rule in definition.rules
        if rule.key not in _RECAP_SKIP
    )
    return "；".join(parts)
