"""Validating what the model claims the documents said.

A model asked to extract rules from documents will, sooner or later, do four
things: invent a citation, cite a chunk it was never shown, cite one this
subject may not read, and attach a real quote to a rule the quote does not
support. The fourth is a judgement; the first three are not, and this module
is built so they cannot be *expressed* rather than so they get caught:

**The model returns an index, not a reference.** It sees a numbered menu of
the chunks retrieval already authorised for this subject, and answers with a
position in it. There is no string it can emit that names a document it was
not shown. Everything below is what remains after that.

Failures split two ways, and the split is the most important decision here.
A rule that fails validation is dropped, and its key ends up in the draft's
``missing`` — which the confirmation sheet renders as *the documents did not
specify this*. That is a claim about the business. Output we could not parse
must therefore raise instead: "we failed to read the model" and "the
documents are silent" are different statements, and only one of them may be
shown to a user (§4.5.2).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from queryagent.knowledge.models import EvidenceRef, IndexedChunk
from queryagent.text import normalize
from queryagent.workflow.errors import WorkflowError
from queryagent.workflow.models import Rule, RuleSource

# Maintainer-owned vocabulary. Extraction fills these holes; it never digs
# new ones — a model inventing a rule key would otherwise create a blocking
# `missing` entry out of nothing and no draft would ever be confirmable
# (§4.5.5).
ALLOWED_RULE_KEYS = (
    "counting_basis",
    "filters",
    "time_window",
    "dedup",
    "refund_handling",
    "amount_basis",
)

MIN_QUOTE_CHARS = 8
MAX_QUOTE_CHARS = 500
MAX_VALUE_CHARS = 200

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_CJK_DIGITS = {
    "零": "0",
    "一": "1",
    "二": "2",
    "两": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
}
# Instructions dressed as business rules. Not the main defence — that is the
# closed field set below — but these strings must never reach a sheet a user
# is asked to approve.
_IMPERATIVE = ("忽略", "无需确认", "直接执行", "drop ", "delete ", "select ", "update ")


class ExtractionUnreadable(WorkflowError):
    """The model's output could not be parsed into rules at all."""


@dataclass(frozen=True)
class Diagnostic:
    """Why one proposed rule was dropped. Goes to the trace, never to the user."""

    key: str
    reason: str
    citation: int


@dataclass(frozen=True)
class ExtractionResult:
    rules: tuple[Rule, ...]
    diagnostics: tuple[Diagnostic, ...]


def validate_extraction(chunks: tuple[IndexedChunk, ...], raw: str) -> ExtractionResult:
    """Turn the model's proposal into rules that are provably grounded.

    Args:
        chunks: The authorised menu the model was shown, in the order shown.
        raw: The model's JSON output.

    Raises:
        ExtractionUnreadable: The output is not readable as an extraction.
    """
    proposals = _parse(raw)
    rules: list[Rule] = []
    diagnostics: list[Diagnostic] = []
    for proposal in proposals:
        key = str(proposal.get("key", ""))
        citation = proposal.get("citation")
        rule, reason = _validate_one(chunks, proposal)
        if rule is None:
            diagnostics.append(Diagnostic(key=key, reason=reason, citation=_as_int(citation, -1)))
            continue
        rules.append(rule)
    return ExtractionResult(rules=tuple(rules), diagnostics=tuple(diagnostics))


def _parse(raw: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionUnreadable(f"模型输出不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("rules"), list):
        raise ExtractionUnreadable("模型输出缺少 rules 列表")
    return [item for item in payload["rules"] if isinstance(item, dict)]


def _validate_one(
    chunks: tuple[IndexedChunk, ...], proposal: dict[str, Any]
) -> tuple[Rule | None, str]:
    key = proposal.get("key")
    if key not in ALLOWED_RULE_KEYS:
        return None, f"规则键不在维护者声明的集合内：{key!r}"

    index = _as_int(proposal.get("citation"), -1)
    if not 0 <= index < len(chunks):
        return None, f"引用下标越界：{proposal.get('citation')!r}"
    chunk = chunks[index]

    value = str(proposal.get("value", "")).strip()
    if not value:
        return None, "规则取值为空"
    if len(value) > MAX_VALUE_CHARS:
        return None, f"规则取值超过 {MAX_VALUE_CHARS} 字符"
    value = " ".join(value.split())
    lowered = value.lower()
    if any(marker in lowered for marker in _IMPERATIVE):
        # Dropped, never cleaned: a scrubbed value is a new string no model,
        # document or person ever reviewed, and labelling *that* 「文档依据」
        # is worse than losing the rule.
        return None, "规则取值含命令式文本，不作为文档依据采纳"

    quote = normalize(str(proposal.get("quote", "")))
    if not MIN_QUOTE_CHARS <= len(quote) <= MAX_QUOTE_CHARS:
        return None, f"引文长度不在 [{MIN_QUOTE_CHARS}, {MAX_QUOTE_CHARS}] 内"
    start = chunk.text.find(quote)
    if start < 0:
        return None, "引文不是被引片段的逐字子串"
    if not _numbers_grounded(value, quote):
        return None, "规则取值中的数字未出现在引文中"

    ref = EvidenceRef(
        doc_id=chunk.doc_id,
        chunk_id=chunk.chunk_id,
        quote_start=start,
        quote_end=start + len(quote),
        content_hash=chunk.content_hash,
    )
    return Rule(key=str(key), value=value, source=RuleSource.DOC, evidence_ref=ref.render()), ""


def _numbers_grounded(value: str, quote: str) -> bool:
    """Every number in the rule must appear in the text it cites.

    The cheapest check that catches the most expensive error class. A
    paraphrase is expected and fine; 「7 天」 rewritten as 「30 天」 is a wrong
    number under a correct-looking citation, and nothing downstream would
    notice. Chinese numerals are folded to digits so 「七天」 still matches
    「7 天」; the table is deliberately small, and an unmapped numeral simply
    fails the check rather than being guessed at.
    """
    quote_numbers = set(_NUMBER.findall(_fold_numerals(quote)))
    return all(number in quote_numbers for number in _NUMBER.findall(_fold_numerals(value)))


def _fold_numerals(text: str) -> str:
    return "".join(_CJK_DIGITS.get(char, char) for char in text)


def _as_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default
