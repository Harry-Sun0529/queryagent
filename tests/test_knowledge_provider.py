"""Slice 1B: authorised retrieval. Permission is the query, not a filter.

Parsing and chunking are proven in test_knowledge_loaders.py and
test_knowledge_chunker.py; this file proves only who can see what.

The recurring assertion: text belonging to another workspace never appears
in *any* field of *any* returned object. Checking that the caller filtered
afterwards would be checking the wrong thing — by then the text has already
been in memory the model's prompt is built from.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from queryagent.knowledge.errors import EvidenceUnavailable
from queryagent.knowledge.index import SqliteKnowledgeIndex
from queryagent.knowledge.models import RefStatus
from queryagent.knowledge.provider import LocalKnowledgeProvider, scope_of
from queryagent.workflow.models import ActorContext

ALICE = ActorContext(subject_id="alice", workspace_id="ops")
MALLORY = ActorContext(subject_id="mallory", workspace_id="finance")

OPS_DOC = """\
# 新增用户口径

运营口径按 users.created_at 注册日期计数。

不含 channel='internal_test' 的测试账号。
"""

FINANCE_DOC = """\
# 新增用户口径

财务口径按 users.first_order_at 首单日期计数。

从未下单的用户不计入。
"""

SECRET = "从未下单的用户不计入"


@pytest.fixture
def provider(tmp_path: Path) -> LocalKnowledgeProvider:
    ops = tmp_path / "ops"
    finance = tmp_path / "finance"
    ops.mkdir()
    finance.mkdir()
    (ops / "handbook.md").write_text(OPS_DOC, encoding="utf-8")
    (finance / "handbook.md").write_text(FINANCE_DOC, encoding="utf-8")
    index = SqliteKnowledgeIndex(tmp_path / "kb.db")
    index.import_directory(ops, workspace_id="ops")
    index.import_directory(finance, workspace_id="finance")
    return LocalKnowledgeProvider(index)


# ------------------------------------------------------------------ K3


def test_search_returns_only_the_actors_workspace(
    provider: LocalKnowledgeProvider,
) -> None:
    hits = provider.search(scope_of(ALICE), "新增用户", limit=10)
    assert hits
    assert all(hit.chunk.workspace_id == "ops" for hit in hits)


def test_another_workspaces_text_appears_in_no_returned_field(
    provider: LocalKnowledgeProvider,
) -> None:
    """K3/T06: not filtered afterwards — never retrieved at all."""
    hits = provider.search(scope_of(ALICE), "新增用户 首单 未下单", limit=50)
    rendered = repr(hits)
    assert SECRET not in rendered
    assert "first_order_at" not in rendered


def test_reading_another_workspaces_chunk_is_refused(
    provider: LocalKnowledgeProvider,
) -> None:
    """A ref leaked by any means still does not read across the boundary."""
    finance_hit = provider.search(scope_of(MALLORY), "新增用户", limit=1)[0]
    with pytest.raises(EvidenceUnavailable):
        provider.read(scope_of(ALICE), finance_hit.ref)


def test_a_refused_read_does_not_reveal_whether_the_chunk_exists(
    provider: LocalKnowledgeProvider,
) -> None:
    """Distinguishing 'revoked' from 'never existed' is itself a disclosure."""
    finance_hit = provider.search(scope_of(MALLORY), "新增用户", limit=1)[0]
    with pytest.raises(EvidenceUnavailable) as denied:
        provider.read(scope_of(ALICE), finance_hit.ref)
    with pytest.raises(EvidenceUnavailable) as missing:
        provider.read(scope_of(ALICE), finance_hit.ref.replace(chunk_id="nope"))
    assert str(denied.value) == str(missing.value)


# ------------------------------------------------------------ retrieval


def test_search_matches_a_paraphrase_through_shared_terms(
    provider: LocalKnowledgeProvider,
) -> None:
    hits = provider.search(scope_of(ALICE), "测试账号要排除吗", limit=5)
    assert any("internal_test" in hit.chunk.text for hit in hits)


def test_an_unrelated_question_retrieves_nothing(
    provider: LocalKnowledgeProvider,
) -> None:
    """T25: no evidence is a fact to report, not a gap to fill with the top hit."""
    assert provider.search(scope_of(ALICE), "机房温度多少", limit=5) == ()


def test_limit_is_respected(provider: LocalKnowledgeProvider) -> None:
    assert len(provider.search(scope_of(ALICE), "新增用户 测试账号", limit=1)) == 1


# ------------------------------------------------------- check_refs (K5)


def test_check_refs_reports_current_evidence_as_ok(
    provider: LocalKnowledgeProvider,
) -> None:
    hit = provider.search(scope_of(ALICE), "新增用户", limit=1)[0]
    assert provider.check_refs(scope_of(ALICE), (hit.ref,)) == (RefStatus.OK,)


def test_editing_the_document_marks_the_ref_changed(
    provider: LocalKnowledgeProvider, tmp_path: Path
) -> None:
    """K5: content hash, not mtime — a reformat must not expire confirmations."""
    hit = provider.search(scope_of(ALICE), "新增用户", limit=1)[0]
    (tmp_path / "ops" / "handbook.md").write_text(
        OPS_DOC.replace("注册日期", "首单日期"), encoding="utf-8"
    )
    provider.index.import_directory(tmp_path / "ops", workspace_id="ops")
    assert provider.check_refs(scope_of(ALICE), (hit.ref,)) == (RefStatus.CHANGED,)


def test_revoking_access_marks_the_ref_unavailable(
    provider: LocalKnowledgeProvider, tmp_path: Path
) -> None:
    hit = provider.search(scope_of(ALICE), "新增用户", limit=1)[0]
    provider.index.revoke_workspace("ops")
    assert provider.check_refs(scope_of(ALICE), (hit.ref,)) == (RefStatus.UNAVAILABLE,)


def test_a_deleted_and_a_revoked_ref_are_indistinguishable(
    provider: LocalKnowledgeProvider,
) -> None:
    """Same reason as the read path: existence is itself information."""
    hit = provider.search(scope_of(ALICE), "新增用户", limit=1)[0]
    provider.index.revoke_workspace("ops")
    revoked = provider.check_refs(scope_of(ALICE), (hit.ref,))
    absent = provider.check_refs(scope_of(ALICE), (hit.ref.replace(chunk_id="gone"),))
    assert revoked == absent == (RefStatus.UNAVAILABLE,)


# ----------------------------------------------------------- ref identity


def test_a_ref_survives_a_reimport_of_unchanged_content(
    provider: LocalKnowledgeProvider, tmp_path: Path
) -> None:
    """§4.5.4: re-indexing must not invalidate every stored confirmation."""
    before = provider.search(scope_of(ALICE), "新增用户", limit=1)[0].ref
    provider.index.import_directory(tmp_path / "ops", workspace_id="ops")
    assert provider.check_refs(scope_of(ALICE), (before,)) == (RefStatus.OK,)
