"""Slice 1C-2: a document rule corresponds to a reading, or no claim is made (T39).

Pure functions: matching a verified quote against the words a maintainer
declared, the verdict against the chosen reading, and choosing a reading the
documents agree on. How the words reach a draft is test_evidence_builder.py;
how the verdicts reach the user, test_cli_flow.py.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from queryagent.workflow.enforcement import (
    CONFLICTS,
    ENFORCED,
    UNCHECKED,
    consistent_variant,
    enforcement_table,
    implied_variants,
    preselect_variant,
    verdict,
)
from queryagent.workflow.mappings import QueryMapping, load_mappings
from queryagent.workflow.models import (
    VARIANT_RULE_KEY,
    BusinessDefinition,
    Candidate,
    Rule,
    RuleSource,
)

TERMS = {
    "registered": {"counting_basis": ("created_at", "注册日期"), "filters": ("internal_test",)},
    "first_order": {
        "counting_basis": ("first_order_at", "首单日期"),
        "filters": ("internal_test",),
    },
}
OPS_QUOTE = "新增用户按 `users.created_at` 的注册日期计数"
GROWTH_QUOTE = "新增用户按 `users.first_order_at` 的首单日期计数"
FILTER_QUOTE = "不计入 `channel = 'internal_test'` 的测试账号"


def test_a_quote_in_one_readings_words_corresponds_to_that_reading() -> None:
    assert implied_variants(TERMS, "counting_basis", OPS_QUOTE) == ("registered",)
    assert implied_variants(TERMS, "counting_basis", GROWTH_QUOTE) == ("first_order",)


def test_a_rule_every_reading_applies_corresponds_to_all_of_them() -> None:
    assert implied_variants(TERMS, "filters", FILTER_QUOTE) == ("first_order", "registered")


def test_a_quote_naming_two_readings_claims_neither() -> None:
    """E11: substring matching cannot tell which of the two it means."""
    assert implied_variants(TERMS, "counting_basis", "不按注册日期，而按首单日期计数") == ()


def test_a_word_only_one_reading_declares_singles_it_out_over_shared_words() -> None:
    """E11 sharpened in review: words {x, y} against {x} is reading a, not both."""
    terms = {"a": {"counting_basis": ("注册", "created_at")}, "b": {"counting_basis": ("注册",)}}
    assert implied_variants(terms, "counting_basis", "按注册的 created_at 计数") == ("a",)


def test_a_key_no_reading_declares_corresponds_to_nothing() -> None:
    assert implied_variants(TERMS, "dedup", OPS_QUOTE) == ()


def test_matching_ignores_case_and_width() -> None:
    assert implied_variants(TERMS, "counting_basis", "按 USERS.CREATED_AT 计数") == ("registered",)


@pytest.mark.parametrize(
    ("implies", "chosen", "expected"),
    [
        (("registered",), "registered", ENFORCED),
        (("first_order", "registered"), "registered", ENFORCED),
        (("first_order",), "registered", CONFLICTS),
        ((), "registered", UNCHECKED),
        (("registered",), "", UNCHECKED),
    ],
)
def test_a_rule_is_applied_contradicted_or_unchecked_by_the_chosen_reading(
    implies: tuple[str, ...], chosen: str, expected: str
) -> None:
    assert verdict(implies, chosen) == expected


def test_the_table_is_built_from_structured_mappings_only() -> None:
    table = enforcement_table(
        {
            ("new_users", "registered"): QueryMapping(
                "users",
                "COUNT(*)",
                "n",
                "created_at",
                enforces=(("counting_basis", ("created_at",)),),
            ),
            ("new_users", "first_order"): QueryMapping("users", "COUNT(*)", "n"),
            ("legacy", ""): "SELECT 1",
        }
    )
    assert table == {"new_users": {"registered": {"counting_basis": ("created_at",)}}}


# ------------------------------------------------------------- preselection

VARIANTS = (
    Candidate("registered", "注册口径", "按 users.created_at 归属日期计数"),
    Candidate("first_order", "首单口径", "按 users.first_order_at 归属日期计数"),
)


def _doc(key: str, implies: tuple[str, ...], ref: str = "d1#c1@0:10") -> Rule:
    return Rule(key, "…", RuleSource.DOC, evidence_ref=ref, implies=implies)


def _draft(*rules: Rule, candidates: tuple[Candidate, ...] = VARIANTS, missing=("variant",)):  # type: ignore[no-untyped-def]
    return BusinessDefinition(
        metric="new_users",
        display_name="新增用户",
        rules=rules,
        missing=missing,
        candidates=candidates,
    )


def test_documents_agreeing_on_one_reading_fill_it_as_document_evidence() -> None:
    """F12: the one path by which a handbook sentence reaches the SQL."""
    definition = preselect_variant(
        _draft(
            _doc("counting_basis", ("registered",)), _doc("filters", ("first_order", "registered"))
        )
    )
    rule = definition.rule(VARIANT_RULE_KEY)
    assert rule is not None
    assert (rule.value, rule.source, rule.evidence_ref) == (
        "registered",
        RuleSource.DOC,
        "d1#c1@0:10",
    )
    assert VARIANT_RULE_KEY not in definition.missing


def test_rules_every_reading_applies_choose_nothing() -> None:
    definition = preselect_variant(_draft(_doc("filters", ("first_order", "registered"))))
    assert definition.rule(VARIANT_RULE_KEY) is None


def test_documents_pointing_different_ways_choose_nothing() -> None:
    definition = preselect_variant(
        _draft(_doc("counting_basis", ("registered",)), _doc("dedup", ("first_order",)))
    )
    assert definition.rule(VARIANT_RULE_KEY) is None


def test_nothing_is_chosen_while_a_document_disagreement_is_open() -> None:
    disagreement = (
        Candidate("counting_basis:0", "按注册日期", "按注册日期", "d1#c1@0:9", ("registered",)),
        Candidate("counting_basis:1", "按首单日期", "按首单日期", "d2#c2@0:9", ("first_order",)),
    )
    definition = preselect_variant(
        _draft(
            _doc("filters", ("first_order", "registered")),
            candidates=VARIANTS + disagreement,
            missing=("variant", "counting_basis"),
        )
    )
    assert definition.rule(VARIANT_RULE_KEY) is None


def test_an_adopted_reading_narrows_the_choice_to_its_variant() -> None:
    """F13: the user's adoption, carrying its document's correspondence."""
    adopted = Rule(
        "counting_basis",
        "按首单日期",
        RuleSource.USER,
        evidence_ref="d2#c2@0:9",
        implies=("first_order",),
    )
    found = consistent_variant([adopted], {"registered", "first_order"})
    assert found == ("first_order", adopted)


# ------------------------------------------------------------- hashing, loading


def test_a_draft_without_correspondences_hashes_exactly_as_before() -> None:
    """Confirmations recorded by v0.7 must still match their drafts."""
    rule = Rule("counting_basis", "按注册日期", RuleSource.DOC, evidence_ref="d1#c1@0:9")
    definition = BusinessDefinition(
        metric="m", display_name="M", rules=(rule,), candidates=VARIANTS
    )
    payload = {
        "metric": "m",
        "rules": [["counting_basis", "按注册日期", "doc", "d1#c1@0:9"]],
        "missing": [],
        "candidates": sorted([c.key, c.label, c.summary, c.evidence_ref] for c in VARIANTS),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert definition.content_hash() == hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def test_which_reading_a_quote_corresponds_to_is_part_of_what_was_confirmed() -> None:
    plain = Rule("counting_basis", "按注册日期", RuleSource.DOC, evidence_ref="d1#c1@0:9")
    matched = Rule(
        "counting_basis",
        "按注册日期",
        RuleSource.DOC,
        evidence_ref="d1#c1@0:9",
        implies=("registered",),
    )
    assert (
        BusinessDefinition("m", "M", rules=(plain,)).content_hash()
        != BusinessDefinition("m", "M", rules=(matched,)).content_hash()
    )


def test_the_shipped_mappings_declare_what_each_reading_applies() -> None:
    table = enforcement_table(load_mappings("examples/query_mappings.yaml"))
    assert implied_variants(table["new_users"], "counting_basis", OPS_QUOTE) == ("registered",)
    assert implied_variants(table["new_users"], "counting_basis", GROWTH_QUOTE) == ("first_order",)


@pytest.mark.parametrize(
    ("enforces", "complaint"),
    [
        ("    enforces: {period: [x]}\n", "not a rule key"),
        ("    enforces: {filters: []}\n", "non-empty list"),
        ("    enforces: [filters]\n", "must map rule keys"),
    ],
)
def test_malformed_enforces_is_refused_at_load(
    tmp_path: Path, enforces: str, complaint: str
) -> None:
    path = tmp_path / "m.yaml"
    path.write_text(
        "mappings:\n  - metric: m\n    from: t\n    measure: COUNT(*)\n    label: n\n" + enforces,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=complaint):
        load_mappings(path)
