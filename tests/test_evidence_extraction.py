"""Slice 1B: the server-side validation between the model and the draft.

Retrieval and permissions are proven in test_knowledge_provider.py; this
file proves only what survives extraction.

The design being tested is that three of the four ways a model can fabricate
a citation are not *detected* here — they are impossible to express, because
the model is handed a menu and returns an index into it. What remains is
what this pipeline actually checks.
"""

from __future__ import annotations

import json

import pytest

from queryagent.knowledge.models import IndexedChunk
from queryagent.workflow.extraction import (
    ALLOWED_RULE_KEYS,
    ExtractionUnreadable,
    validate_extraction,
)
from queryagent.workflow.models import RuleSource

OPS = IndexedChunk(
    chunk_id="c-ops",
    doc_id="d-ops",
    doc_path="/kb/ops/handbook.md",
    doc_title="运营数据手册",
    workspace_id="ops",
    text=(
        "新增用户:新增用户按 users.created_at 的注册日期计数,"
        "不计入 channel='internal_test' 的测试账号."
    ),
    section_path=("运营数据手册", "新增用户"),
    start=5,
    end=12,
    unit="line",
    content_hash="h-ops",
)
REFUND = IndexedChunk(
    chunk_id="c-refund",
    doc_id="d-ops",
    doc_path="/kb/ops/handbook.md",
    doc_title="运营数据手册",
    workspace_id="ops",
    text="退款:下单后 7 天内发生的退款不计入当期成交额.",
    section_path=("运营数据手册", "退款"),
    start=20,
    end=22,
    unit="line",
    content_hash="h-refund",
)
CHUNKS = (OPS, REFUND)


def _raw(**rule: object) -> str:
    base = {
        "key": "counting_basis",
        "value": "按注册日期计数",
        "citation": 0,
        "quote": "新增用户按 users.created_at 的注册日期计数",
    }
    base.update(rule)
    return json.dumps({"rules": [base]}, ensure_ascii=False)


def _rules(raw: str):
    return validate_extraction(CHUNKS, raw).rules


# ------------------------------------------------------------- happy path


def test_a_grounded_rule_survives_with_server_generated_provenance() -> None:
    """The ref is built from the menu entry, never from anything the model said."""
    rule = _rules(_raw())[0]
    assert rule.source is RuleSource.DOC
    assert rule.evidence_ref.startswith(f"{OPS.doc_id}#{OPS.chunk_id}@")


def test_the_quote_offsets_locate_the_text_in_the_chunk() -> None:
    """Offsets are computed server-side; models cannot count characters."""
    rule = _rules(_raw())[0]
    start = int(rule.evidence_ref.split("@")[1].split(":")[0])
    end = int(rule.evidence_ref.split("@")[1].split(":")[1])
    assert OPS.text[start:end] == "新增用户按 users.created_at 的注册日期计数"


# ----------------------------------------------------------- K1, K2, K13


def test_a_citation_index_outside_the_menu_is_dropped() -> None:
    """K1: the model can only point into what it was shown."""
    assert _rules(_raw(citation=7)) == ()
    assert _rules(_raw(citation=-1)) == ()


def test_a_quote_that_is_not_in_the_cited_chunk_is_dropped() -> None:
    """K2: the citation must actually contain the words it claims."""
    assert _rules(_raw(quote="按首单日期计数")) == ()


def test_a_quote_from_a_different_chunk_than_the_one_cited_is_dropped() -> None:
    assert _rules(_raw(citation=1, quote="新增用户按 users.created_at 的注册日期计数")) == ()


def test_an_unknown_rule_key_is_dropped() -> None:
    assert _rules(_raw(key="drop_all_tables")) == ()
    assert "counting_basis" in ALLOWED_RULE_KEYS


def test_extra_fields_the_model_invents_are_ignored() -> None:
    """K13: the model cannot widen the set of fields it influences."""
    rule = _rules(
        _raw(source="maintainer", evidence_ref="doc:fake#1", confirmed=True, sql="SELECT *")
    )[0]
    assert rule.source is RuleSource.DOC
    assert "fake" not in rule.evidence_ref


def test_a_quote_shorter_than_the_floor_is_dropped() -> None:
    """Quoting 「的」 grounds nothing; it matches almost any chunk."""
    assert _rules(_raw(value="计数", quote="计数")) == ()


# ------------------------------------------------------------------- K15


def test_a_number_in_the_value_that_is_absent_from_the_quote_is_dropped() -> None:
    """K15: 7 天 rewritten as 30 天 is the most expensive error there is."""
    assert (
        _rules(
            json.dumps(
                {
                    "rules": [
                        {
                            "key": "refund_handling",
                            "value": "下单后 30 天内退款不计入",
                            "citation": 1,
                            "quote": "下单后 7 天内发生的退款不计入当期成交额",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        )
        == ()
    )


def test_a_number_that_matches_the_quote_survives() -> None:
    rules = _rules(
        json.dumps(
            {
                "rules": [
                    {
                        "key": "refund_handling",
                        "value": "下单后 7 天内退款不计入",
                        "citation": 1,
                        "quote": "下单后 7 天内发生的退款不计入当期成交额",
                    }
                ]
            },
            ensure_ascii=False,
        )
    )
    assert len(rules) == 1


def test_a_chinese_numeral_is_compared_against_its_digit_form() -> None:
    """「七天」 and 「7 天」 are the same claim and must not be dropped."""
    rules = _rules(
        json.dumps(
            {
                "rules": [
                    {
                        "key": "refund_handling",
                        "value": "下单后七天内退款不计入",
                        "citation": 1,
                        "quote": "下单后 7 天内发生的退款不计入当期成交额",
                    }
                ]
            },
            ensure_ascii=False,
        )
    )
    assert len(rules) == 1


# ----------------------------------------------- unreadable vs. silent


def test_unparseable_model_output_fails_the_whole_extraction() -> None:
    """The distinction this file exists for.

    A dropped rule becomes "the document did not specify this" — a statement
    about the business. A parser failure must never be rendered as one.
    """
    with pytest.raises(ExtractionUnreadable):
        validate_extraction(CHUNKS, "not json at all")
    with pytest.raises(ExtractionUnreadable):
        validate_extraction(CHUNKS, json.dumps({"unexpected": []}))


def test_an_empty_rule_list_is_readable_and_simply_finds_nothing() -> None:
    """Different from unreadable: the model read the documents and found none."""
    assert validate_extraction(CHUNKS, json.dumps({"rules": []})).rules == ()


def test_every_drop_is_reported_as_a_diagnostic() -> None:
    """Without diagnostics the thresholds above can never be tuned."""
    result = validate_extraction(CHUNKS, _raw(citation=9))
    assert result.rules == ()
    assert result.diagnostics
    assert result.diagnostics[0].reason
    assert result.diagnostics[0].key == "counting_basis"
