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

from collections.abc import Mapping

from queryagent.workflow.builder import VARIANT_RULE_KEY
from queryagent.workflow.coverage import (
    confirmed_period,
    describe_coverage,
    describe_emptiness,
    latest_date,
)
from queryagent.workflow.enforcement import CONFLICTS, ENFORCED, verdict
from queryagent.workflow.grouping import (
    MONTH,
    TIME_GRAINS,
    WEEK,
    bucket_starts,
    edges_are_partial,
    filter_text,
    grouping_text,
)
from queryagent.workflow.models import (
    COMPILED_RULE_KEYS,
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    PREVIOUS_CHOICE_KEY,
    BusinessDefinition,
    Candidate,
    DefinitionDraft,
    QueryRun,
    Rule,
    RuleSource,
)
from queryagent.workflow.periods import Period

_SOURCE_LABELS = {
    RuleSource.DOC: "文档依据",
    RuleSource.USER: "本次约定",
    RuleSource.MAINTAINER: "系统映射",
    RuleSource.HISTORY: "历史选择",
}

_RULE_LABELS = {
    "metric": "统计对象",
    "definition": "指标说明",
    "tables": "涉及数据表",
    "variant": "选定口径",
    "period": "统计区间",
    "group_by": "分组方式",
    PREVIOUS_CHOICE_KEY: "上次的选择",
    FILTER_RULE_KEY: "取值过滤",
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


def _candidate_lines(
    candidates: list[Candidate],
    citations: dict[str, str] | None,
    definition: BusinessDefinition | None = None,
) -> list[str]:
    lines = []
    for candidate in candidates:
        summary = f" — {candidate.summary}" if candidate.summary != candidate.label else ""
        lines.append(f"  [{candidate.key}] {candidate.label}{summary}")
        where = _location(citations, candidate.evidence_ref)
        if where:
            lines.append(f"      出处：{where}")
        if definition is not None and candidate.implies:
            names = _variant_names(definition, candidate.implies)
            lines.append(f"      → 对应可执行口径：{names}")
    return lines


def _chosen_variant(definition: BusinessDefinition) -> str:
    rule = definition.rule(VARIANT_RULE_KEY)
    return rule.value if rule else ""


def _variant_names(definition: BusinessDefinition, keys: tuple[str, ...]) -> str:
    names = []
    for key in keys:
        candidate = definition.candidate(key)
        names.append(candidate.label if candidate else key)
    return "、".join(names)


def _correspondence(definition: BusinessDefinition, rule: Rule) -> str:
    """One line tying a document rule to what runs, or '' (T39).

    Only what the maintainer's declared words establish: the quote contains
    wording this reading's SQL answers to. Whether the sentence *means* that
    is on the sheet, beside its source, for the reader.
    """
    if not rule.implies or rule.key == VARIANT_RULE_KEY:
        return ""
    chosen = _chosen_variant(definition)
    outcome = verdict(rule.implies, chosen)
    if outcome == ENFORCED:
        return f"→ 已由所选口径（{_variant_names(definition, (chosen,))}）执行"
    names = _variant_names(definition, rule.implies)
    if outcome == CONFLICTS:
        running = _variant_names(definition, (chosen,))
        return f"✗ 与所选口径不一致：这段原文对应「{names}」，执行的是「{running}」"
    return f"→ 对应可执行口径：{names}"


def _rule_text(
    definition: BusinessDefinition, rule: Rule, labels: Mapping[str, str] | None = None
) -> str:
    """Render a rule's value for a human.

    A variant rule's value is a lookup key — meaningful to the compiler,
    meaningless to the operator who has to repeat this 口径 to a colleague.
    Show the maintainer's own wording instead (D04).
    """
    if rule.key == PERIOD_RULE_KEY:
        try:
            return _noted(Period.decode(rule.value).render(), rule)
        except ValueError:
            return rule.value
    if rule.key == GROUP_RULE_KEY:
        return _noted(grouping_text(rule.value, labels), rule)
    if rule.key == FILTER_RULE_KEY:
        return _noted(filter_text(rule.value, labels), rule)
    if rule.key == VARIANT_RULE_KEY:
        candidate = definition.candidate(rule.value)
        if candidate is not None:
            return f"{candidate.label} — {candidate.summary}"
    return rule.value


def _noted(text: str, rule: Rule) -> str:
    """A rule's rendered value, with the words it was read from when there are any."""
    return f"{text}（{rule.note}）" if rule.note else text


def render_draft(
    draft: DefinitionDraft,
    citations: dict[str, str] | None = None,
    labels: Mapping[str, str] | None = None,
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
        text = _rule_text(definition, rule, labels)
        if rule.source is RuleSource.HISTORY and rule.key != PREVIOUS_CHOICE_KEY:
            text = f"{text}（{rule.note}）"  # G12: which earlier day it repeats
        lines.append(f"  · {label}：{text}    [{mark}]")
        where = _location(citations, rule.evidence_ref)
        if where:
            lines.append(f"      出处：{where}")
        correspondence = _correspondence(definition, rule)
        if correspondence:
            lines.append(f"      {correspondence}")
    variants = [c for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY]
    disagreements: dict[str, list[Candidate]] = {}
    for candidate in definition.candidates:
        if candidate.rule_key != VARIANT_RULE_KEY:
            disagreements.setdefault(candidate.rule_key, []).append(candidate)
    if variants:
        # Once a reading is chosen — by the user, or by documents agreeing
        # (T39) — "you need to pick one" would ask for a choice already made.
        header = (
            "可选口径（维护者定义的可执行取法，需要你选一个）："
            if VARIANT_RULE_KEY in definition.missing
            else "可选口径（维护者定义的可执行取法；已选定的见上方「选定口径」）："
        )
        lines.extend(["", header])
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
        lines.extend(_candidate_lines(options, citations, definition))
    if definition.missing:
        missing = "、".join(_RULE_LABELS.get(key, key) for key in definition.missing)
        lines.extend(["", f"尚未确定：{missing}（确定前不会执行任何查询）"])
    lines.extend(["", f"内容指纹：{draft.definition_hash[:16]}"])
    return "\n".join(lines)


def render_definition_summary(
    definition: BusinessDefinition, labels: Mapping[str, str] | None = None
) -> str:
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
        f"{rule_label(rule.key)}={_rule_text(definition, rule, labels)}"
        for rule in definition.rules
        if rule.key in COMPILED_RULE_KEYS
    )
    # Document rules the chosen reading's SQL applies, by the maintainer's own
    # declaration (T39) — the one kind of explanatory rule the number honours.
    chosen = _chosen_variant(definition)
    parts.extend(
        f"{rule_label(rule.key)}={rule.value.rstrip('。')}"
        for rule in definition.rules
        if rule.key not in COMPILED_RULE_KEYS and verdict(rule.implies, chosen) == ENFORCED
    )
    if definition.rule(PERIOD_RULE_KEY) is None:
        # Said out loud (P9): no window is a fact about this number, not a
        # default the reader should have to work out from the SQL.
        parts.append(f"{rule_label(PERIOD_RULE_KEY)}=未限定（全部数据）")
    return "；".join(parts)


def render_coverage(definition: BusinessDefinition, run: QueryRun) -> str:
    """How far the data behind this run reaches, against its period, or ''."""
    return describe_coverage(
        confirmed_period(definition),
        latest_date(run.data_through),
        probed=bool(run.freshness_sql),
    )


def render_emptiness(definition: BusinessDefinition, run: QueryRun) -> str:
    """Why this run has nothing to report, when it has nothing to report, or ''."""
    return describe_emptiness(
        run.rows, confirmed_period(definition), latest_date(run.data_through)
    )


def _cell(value: object) -> str:
    return "NULL" if value is None else str(value)


def render_rows(definition: BusinessDefinition, run: QueryRun) -> list[str]:
    """The result table as lines, header first.

    Split by time over a confirmed period, every group in the period gets a
    line. Otherwise a day with no records is simply absent, and a reader
    scanning 31 dates for the missing one is how 「23 日没有新增」 gets said
    about a day that has no data at all. Absent groups read 「无记录」 inside
    the data and 「无数据」 after its newest record. A truncated result is
    shown as returned: filling it would label the cut-off tail as empty.
    """
    lines = ["  " + " | ".join(run.columns)]
    rule = definition.rule(GROUP_RULE_KEY)
    period = confirmed_period(definition)
    grain = rule.value if rule else ""
    fillable = grain in TIME_GRAINS and period is not None and len(run.columns) == 2
    if fillable and period is not None and not run.truncated:
        starts = bucket_starts(period, grain)
        values = {latest_date(row[0]): row[1] for row in run.rows}
        if set(values) <= set(starts):
            latest = latest_date(run.data_through)
            for start in starts:
                key = start.isoformat()[:7] if grain == MONTH else start.isoformat()
                if start in values:
                    cell = _cell(values[start])
                elif latest is None:
                    # The probe failed: this group may be empty or past the
                    # data, and saying either would be the confusion F5 is for.
                    cell = "（未知：无记录或尚无数据）"
                elif start > latest:
                    cell = "（无数据）"
                else:
                    cell = "（无记录）"
                lines.append(f"  {key} | {cell}")
            return lines
    lines.extend("  " + " | ".join(_cell(value) for value in row) for row in run.rows)
    return lines


def render_grouping_note(definition: BusinessDefinition) -> str:
    """Say so when the first or last week or month is only partly in the period."""
    rule = definition.rule(GROUP_RULE_KEY)
    period = confirmed_period(definition)
    if rule is None or period is None or not edges_are_partial(period, rule.value):
        return ""
    unit = "周" if rule.value == WEEK else "月"
    return (
        f"按{unit}分组时，首尾两组只统计区间 {period.start} 至 {period.end} 内的日期，"
        f"不是完整的一{unit}。"
    )


def render_conflicts(definition: BusinessDefinition) -> str:
    """Name the document rules the executed reading contradicts, or '' (F14).

    Not a disclaimer: the system knows these disagree, by the maintainer's
    declared wording, and says which way. The number is still the chosen
    reading's — the user may have chosen against the handbook on purpose.
    """
    chosen = _chosen_variant(definition)
    conflicting = [
        rule
        for rule in definition.rules
        if rule.key not in COMPILED_RULE_KEYS and verdict(rule.implies, chosen) == CONFLICTS
    ]
    if not conflicting:
        return ""
    items = "；".join(
        f"{rule_label(rule.key)}（原文对应「{_variant_names(definition, rule.implies)}」）"
        for rule in conflicting
    )
    running = _variant_names(definition, (chosen,))
    return (
        f"与执行不一致：{items}，而执行的是「{running}」。"
        "这个数字按所选口径计算，不符合这些文档规则。"
    )


def render_unenforced(definition: BusinessDefinition) -> str:
    """Name the confirmed rules the executed query did not itself apply, or ''.

    The system cannot tell whether a maintainer's SQL happens to implement a
    handbook sentence, so it says so rather than implying either way.
    """
    chosen = _chosen_variant(definition)
    labels = [
        rule_label(rule.key)
        for rule in definition.rules
        if rule.source is not RuleSource.MAINTAINER
        and rule.key not in COMPILED_RULE_KEYS
        and rule.key != PREVIOUS_CHOICE_KEY
        # Checked ones are said elsewhere: in the result line when the SQL
        # applies them, in render_conflicts when it applies something else.
        and verdict(rule.implies, chosen) not in (ENFORCED, CONFLICTS)
    ]
    if not labels:
        return ""
    return (
        f"说明：{'、'.join(labels)} 来自文档、本次约定或历史选择，用于解释口径；本次执行的是"
        "维护者映射（见下方 SQL），系统不核对两者是否一致。"
    )
