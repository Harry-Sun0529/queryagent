"""v1.0 T48: state files written by 0.6-0.9, by those releases' own code, open in 1.0 (H14).

The fixtures under tests/fixtures/state/ were produced by checking out each
tagged release and running its own `queryagent kb import` and `queryagent
flow` (one draft confirmed and executed, one declined). A hand-written "old"
schema is only as right as someone's memory of it; these are what the
releases actually wrote.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from queryagent.knowledge.index import SqliteKnowledgeIndex
from queryagent.knowledge.models import EvidenceRef, RefStatus
from queryagent.knowledge.provider import LocalKnowledgeProvider, scope_of
from queryagent.workflow.models import (
    ActorContext,
    Channel,
    Confirmation,
    DraftStatus,
    RunStatus,
)
from queryagent.workflow.store import SqliteWorkflowStore

FIXTURES = Path(__file__).parent / "fixtures" / "state"
RELEASES = ("v0.6.0", "v0.7.0", "v0.8.0", "v0.9.0")
WITH_DOCUMENTS = RELEASES[1:]
ALICE = ActorContext(subject_id="alice", workspace_id="ops")


def _copy(tmp_path: Path, release: str, name: str) -> Path:
    target = tmp_path / name
    shutil.copy(FIXTURES / release / name, target)
    return target


def _ids(path: Path, sql: str) -> list[str]:
    with sqlite3.connect(path) as connection:
        return [row[0] for row in connection.execute(sql)]


@pytest.mark.parametrize("release", RELEASES)
def test_a_state_file_from_an_earlier_release_reads_and_upgrades_in_place(
    tmp_path: Path, release: str
) -> None:
    path = _copy(tmp_path, release, "workflow.db")
    confirmation_ids = _ids(path, "SELECT confirmation_id FROM confirmations")
    run_ids = _ids(path, "SELECT run_id FROM runs")
    draft_ids = _ids(path, "SELECT draft_id FROM drafts")
    store = SqliteWorkflowStore(path)

    assert {store.get_draft("alice", d).subject_id for d in draft_ids} == {"alice"}
    (confirmation_id,) = confirmation_ids
    assert store.get_confirmation("alice", confirmation_id).channel is Channel.CLI
    (run_id,) = run_ids
    run = store.get_run("alice", run_id)
    assert run.status is RunStatus.SUCCEEDED
    assert run.rows == ((2,),)

    (declined,) = store.pending_drafts("alice", "ops")
    assert declined.status is DraftStatus.AWAITING_CONFIRMATION
    # The upgraded file takes 1.0's writes: a confirmation from the page.
    store.save_confirmation(
        Confirmation(
            "c-1.0",
            declined.draft_id,
            declined.version,
            declined.definition_hash,
            "alice",
            datetime.now(timezone.utc),
            Channel.WEB,
        )
    )
    found = store.human_confirmation(
        "alice", declined.draft_id, declined.version, declined.definition_hash
    )
    assert found is not None and found.channel is Channel.WEB
    assert store.pending_drafts("alice", "ops") == ()
    store.close()


@pytest.mark.parametrize("release", WITH_DOCUMENTS)
def test_evidence_an_earlier_release_recorded_is_still_rechecked(
    tmp_path: Path, release: str
) -> None:
    """A draft from 0.7-0.9 keeps its citations, and 1.0 can still verify each one."""
    workflow = _copy(tmp_path, release, "workflow.db")
    knowledge = _copy(tmp_path, release, "knowledge.db")
    cited = _ids(workflow, "SELECT DISTINCT draft_id FROM draft_evidence")
    assert cited, "the fixture was meant to hold a draft with document evidence"
    store = SqliteWorkflowStore(workflow)
    index = SqliteKnowledgeIndex(knowledge)
    provider = LocalKnowledgeProvider(index, None)
    for draft_id in cited:
        refs = tuple(EvidenceRef.parse(ref) for ref in store.evidence_of("alice", draft_id))
        statuses = provider.check_refs(scope_of(ALICE), refs)
        assert all(status is RefStatus.OK for status in statuses), statuses
    assert provider.search(scope_of(ALICE), "新增用户", limit=5)
    index.close()
    store.close()
