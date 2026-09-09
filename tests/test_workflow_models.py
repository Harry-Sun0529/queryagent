"""Slice 1A: the confirmable semantic object and its provenance."""

from __future__ import annotations

import pytest

from queryagent.workflow.models import (
    ActorContext,
    BusinessDefinition,
    Rule,
    RuleSource,
)


def _definition(**overrides: object) -> BusinessDefinition:
    base: dict[str, object] = {
        "metric": "new_users",
        "display_name": "新增用户",
        "rules": (
            Rule("counting_basis", "按 users.created_at 注册日期计数", RuleSource.MAINTAINER),
            Rule("filters", "排除 channel='internal_test'", RuleSource.MAINTAINER),
        ),
        "missing": (),
        "candidates": (),
    }
    base.update(overrides)
    return BusinessDefinition(**base)  # type: ignore[arg-type]


def test_hash_is_stable_across_equal_definitions() -> None:
    assert _definition().content_hash() == _definition().content_hash()


def test_changing_a_semantic_rule_changes_the_hash() -> None:
    """§9.2 invariant 4: a different meaning must not reuse an old confirmation."""
    other = _definition(
        rules=(
            Rule("counting_basis", "按 users.first_order_at 首单日期计数", RuleSource.MAINTAINER),
            Rule("filters", "排除 channel='internal_test'", RuleSource.MAINTAINER),
        )
    )
    assert other.content_hash() != _definition().content_hash()


def test_rule_order_does_not_change_meaning() -> None:
    """Display order is presentation; the hash tracks meaning, not layout."""
    reordered = _definition(
        rules=(
            Rule("filters", "排除 channel='internal_test'", RuleSource.MAINTAINER),
            Rule("counting_basis", "按 users.created_at 注册日期计数", RuleSource.MAINTAINER),
        )
    )
    assert reordered.content_hash() == _definition().content_hash()


def test_missing_rules_are_part_of_the_hash() -> None:
    """A draft that still admits it is missing a rule is not the same object."""
    assert _definition(missing=("refund_handling",)).content_hash() != _definition().content_hash()


def test_rule_source_is_recorded_not_inferred() -> None:
    """D07: a user's own convention must never be presented as document fact."""
    user_rule = Rule("refund_handling", "本次不扣退款", RuleSource.USER)
    assert user_rule.source is RuleSource.USER
    assert user_rule.is_user_supplied


def test_a_doc_sourced_rule_requires_an_evidence_ref() -> None:
    """§18: a citation that points nowhere is a fabricated citation."""
    with pytest.raises(ValueError, match="evidence"):
        Rule("counting_basis", "按注册日期", RuleSource.DOC)


def test_actor_context_requires_a_subject() -> None:
    with pytest.raises(ValueError, match="subject_id"):
        ActorContext(subject_id="", workspace_id="ops")


def test_definition_reports_whether_it_is_ready_to_confirm() -> None:
    assert _definition().is_complete
    assert not _definition(missing=("time_window",)).is_complete


def test_rewording_a_candidate_invalidates_the_hash() -> None:
    """The options a user chose between are part of what they approved."""
    from queryagent.workflow.models import Candidate

    original = _definition(candidates=(Candidate("registered", "注册口径", "按注册日期"),))
    reworded = _definition(candidates=(Candidate("registered", "注册口径", "按首单日期"),))
    assert original.content_hash() != reworded.content_hash()
