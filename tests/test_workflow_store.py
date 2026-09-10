"""Slice 1A: server-side state is the source of truth, not the caller."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from queryagent.workflow.errors import PermissionDenied, StaleVersion
from queryagent.workflow.models import (
    BusinessDefinition,
    Confirmation,
    DefinitionDraft,
    DraftStatus,
    QueryRun,
    Rule,
    RuleSource,
    RunStatus,
)
from queryagent.workflow.store import SqliteWorkflowStore

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


def _draft(store_id: str = "d1", *, subject: str = "alice", version: int = 1) -> DefinitionDraft:
    definition = BusinessDefinition(
        metric="new_users",
        display_name="新增用户",
        rules=(Rule("counting_basis", "注册日期", RuleSource.MAINTAINER),),
    )
    return DefinitionDraft(
        draft_id=store_id,
        request_id="req-1",
        subject_id=subject,
        workspace_id="ops",
        question="上个月新增用户多少？",
        version=version,
        status=DraftStatus.AWAITING_CONFIRMATION,
        definition=definition,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def store(tmp_path: Path) -> SqliteWorkflowStore:
    return SqliteWorkflowStore(tmp_path / "workflow.db")


def test_draft_round_trips_including_rule_provenance(store: SqliteWorkflowStore) -> None:
    store.create_draft(_draft())
    loaded = store.get_draft("alice", "d1")
    assert loaded.definition.rules[0].source is RuleSource.MAINTAINER
    assert loaded.definition.content_hash() == _draft().definition.content_hash()


def test_state_survives_reopening_the_store(tmp_path: Path) -> None:
    """§9.2 invariant: a restarted process recovers drafts, not a blank slate (T27)."""
    path = tmp_path / "workflow.db"
    SqliteWorkflowStore(path).create_draft(_draft())
    assert SqliteWorkflowStore(path).get_draft("alice", "d1").question.startswith("上个月")


def test_another_subject_cannot_read_the_draft(store: SqliteWorkflowStore) -> None:
    """T06: ownership is checked in the store, not only in the UI."""
    store.create_draft(_draft())
    with pytest.raises(PermissionDenied):
        store.get_draft("mallory", "d1")


def test_update_requires_the_expected_version(store: SqliteWorkflowStore) -> None:
    """T12: a second editor must lose loudly, not overwrite silently."""
    store.create_draft(_draft())
    store.update_draft("alice", _draft(version=2), expected_version=1)
    with pytest.raises(StaleVersion):
        store.update_draft("alice", _draft(version=3), expected_version=1)
    assert store.get_draft("alice", "d1").version == 2


def test_confirmation_round_trips(store: SqliteWorkflowStore) -> None:
    store.create_draft(_draft())
    confirmation = Confirmation(
        confirmation_id="c1",
        draft_id="d1",
        draft_version=1,
        definition_hash=_draft().definition_hash,
        subject_id="alice",
        confirmed_at=NOW,
    )
    store.save_confirmation(confirmation)
    assert store.get_confirmation("alice", "c1").draft_version == 1
    with pytest.raises(PermissionDenied):
        store.get_confirmation("mallory", "c1")


def test_idempotency_key_claims_are_unique(store: SqliteWorkflowStore) -> None:
    """T13: the second claim of a key returns the first run, and does not create one."""
    store.create_draft(_draft())
    run = QueryRun(
        run_id="r1",
        draft_id="d1",
        confirmation_id="c1",
        subject_id="alice",
        idempotency_key="key-1",
        status=RunStatus.EXECUTING,
    )
    assert store.claim_run(run) is None
    existing = store.claim_run(
        QueryRun(
            run_id="r2",
            draft_id="d1",
            confirmation_id="c1",
            subject_id="alice",
            idempotency_key="key-1",
            status=RunStatus.EXECUTING,
        )
    )
    assert existing is not None
    assert existing.run_id == "r1"


def test_finished_run_is_persisted_with_its_result(store: SqliteWorkflowStore) -> None:
    store.create_draft(_draft())
    run = QueryRun(
        run_id="r1",
        draft_id="d1",
        confirmation_id="c1",
        subject_id="alice",
        idempotency_key="key-1",
        status=RunStatus.EXECUTING,
    )
    store.claim_run(run)
    store.finish_run(
        QueryRun(
            run_id="r1",
            draft_id="d1",
            confirmation_id="c1",
            subject_id="alice",
            idempotency_key="key-1",
            status=RunStatus.SUCCEEDED,
            sql="SELECT 1",
            columns=("n",),
            rows=((7,),),
        )
    )
    loaded = store.get_run("alice", "r1")
    assert loaded.status is RunStatus.SUCCEEDED
    assert loaded.rows == ((7,),)


def test_a_state_file_from_before_bound_values_is_upgraded_in_place(tmp_path: Path) -> None:
    """T36: a v0.7 state file has no params column; its runs stay readable."""
    import sqlite3

    path = tmp_path / "workflow.db"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE runs (run_id TEXT PRIMARY KEY, draft_id TEXT NOT NULL, "
        "confirmation_id TEXT NOT NULL, subject_id TEXT NOT NULL, "
        "idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL, "
        "sql TEXT NOT NULL DEFAULT '', columns TEXT NOT NULL DEFAULT '[]', "
        "rows TEXT NOT NULL DEFAULT '[]', truncated INTEGER NOT NULL DEFAULT 0, "
        "error TEXT NOT NULL DEFAULT '')"
    )
    old.execute(
        "INSERT INTO runs (run_id, draft_id, confirmation_id, subject_id, idempotency_key, "
        "status, sql) VALUES ('r0', 'd0', 'c0', 'alice', 'k0', 'succeeded', 'SELECT 1')"
    )
    old.commit()
    old.close()

    store = SqliteWorkflowStore(path)
    assert store.get_run("alice", "r0").params == ()
    store.create_draft(_draft())
    store.claim_run(
        QueryRun("r1", "d1", "c1", "alice", "k1", RunStatus.EXECUTING, sql="SELECT ?")
    )
    store.finish_run(
        QueryRun(
            "r1", "d1", "c1", "alice", "k1", RunStatus.SUCCEEDED, sql="SELECT ?", params=("x",)
        )
    )
    assert store.get_run("alice", "r1").params == ("x",)


def test_missing_draft_is_reported_as_not_found(store: SqliteWorkflowStore) -> None:
    from queryagent.workflow.errors import NotFound

    with pytest.raises(NotFound):
        store.get_draft("alice", "nope")
