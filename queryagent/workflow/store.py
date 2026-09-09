"""SQLite persistence for drafts, confirmations and runs.

Why the server holds this: a confirmation the client hands back is a claim,
not evidence. Every read is scoped by ``subject_id`` so ownership is enforced
here rather than by whichever entry point happens to call — CLI, Web and MCP
all go through this one door (D13, T26).

Scope boundary: one process, one local file. Multi-replica deployments need
shared coordination before any global claim holds (handoff §7.2).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from queryagent.workflow.errors import NotFound, PermissionDenied, StaleVersion
from queryagent.workflow.models import (
    BusinessDefinition,
    Candidate,
    Confirmation,
    DefinitionDraft,
    DraftStatus,
    QueryRun,
    Rule,
    RuleSource,
    RunStatus,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts (
    draft_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    question TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    definition TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS confirmations (
    confirmation_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    draft_version INTEGER NOT NULL,
    definition_hash TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    confirmed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    confirmation_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    sql TEXT NOT NULL DEFAULT '',
    columns TEXT NOT NULL DEFAULT '[]',
    rows TEXT NOT NULL DEFAULT '[]',
    truncated INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT ''
);
"""


class SqliteWorkflowStore:
    """Durable state for the workflow layer."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ---------------------------------------------------------------- drafts

    def create_draft(self, draft: DefinitionDraft) -> None:
        self._conn.execute(
            "INSERT INTO drafts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                draft.draft_id,
                draft.request_id,
                draft.subject_id,
                draft.workspace_id,
                draft.question,
                draft.version,
                draft.status.value,
                _encode_definition(draft.definition),
                draft.definition_hash,
                draft.created_at.isoformat(),
                draft.updated_at.isoformat(),
            ),
        )

    def get_draft(self, subject_id: str, draft_id: str) -> DefinitionDraft:
        row = self._conn.execute("SELECT * FROM drafts WHERE draft_id = ?", (draft_id,)).fetchone()
        if row is None:
            raise NotFound(f"no such draft: {draft_id}")
        if row["subject_id"] != subject_id:
            raise PermissionDenied("not permitted")
        return _decode_draft(row)

    def update_draft(
        self, subject_id: str, draft: DefinitionDraft, *, expected_version: int
    ) -> None:
        """Optimistic write: the update applies only to ``expected_version``.

        The ownership check runs first so a stranger gets a permission error
        rather than a version error that leaks the current version.
        """
        current = self.get_draft(subject_id, draft.draft_id)
        if current.version != expected_version:
            raise StaleVersion(
                f"draft {draft.draft_id} is at version {current.version}, not {expected_version}"
            )
        cursor = self._conn.execute(
            "UPDATE drafts SET version=?, status=?, definition=?, definition_hash=?, "
            "updated_at=? WHERE draft_id=? AND version=?",
            (
                draft.version,
                draft.status.value,
                _encode_definition(draft.definition),
                draft.definition_hash,
                draft.updated_at.isoformat(),
                draft.draft_id,
                expected_version,
            ),
        )
        if cursor.rowcount != 1:  # pragma: no cover - lost race under concurrency
            raise StaleVersion(f"draft {draft.draft_id} changed during update")

    # --------------------------------------------------------- confirmations

    def save_confirmation(self, confirmation: Confirmation) -> None:
        self._conn.execute(
            "INSERT INTO confirmations VALUES (?,?,?,?,?,?)",
            (
                confirmation.confirmation_id,
                confirmation.draft_id,
                confirmation.draft_version,
                confirmation.definition_hash,
                confirmation.subject_id,
                confirmation.confirmed_at.isoformat(),
            ),
        )

    def get_confirmation(self, subject_id: str, confirmation_id: str) -> Confirmation:
        row = self._conn.execute(
            "SELECT * FROM confirmations WHERE confirmation_id = ?", (confirmation_id,)
        ).fetchone()
        if row is None:
            raise NotFound(f"no such confirmation: {confirmation_id}")
        if row["subject_id"] != subject_id:
            raise PermissionDenied("not permitted")
        return Confirmation(
            confirmation_id=row["confirmation_id"],
            draft_id=row["draft_id"],
            draft_version=row["draft_version"],
            definition_hash=row["definition_hash"],
            subject_id=row["subject_id"],
            confirmed_at=datetime.fromisoformat(row["confirmed_at"]),
        )

    # ------------------------------------------------------------------ runs

    def claim_run(self, run: QueryRun) -> QueryRun | None:
        """Take the idempotency key, or return the run that already holds it.

        The UNIQUE constraint is the arbiter, so a duplicate request cannot
        start a second database query even if two callers race (T13).
        """
        try:
            self._conn.execute(
                "INSERT INTO runs (run_id, draft_id, confirmation_id, subject_id, "
                "idempotency_key, status) VALUES (?,?,?,?,?,?)",
                (
                    run.run_id,
                    run.draft_id,
                    run.confirmation_id,
                    run.subject_id,
                    run.idempotency_key,
                    run.status.value,
                ),
            )
        except sqlite3.IntegrityError:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE idempotency_key = ?", (run.idempotency_key,)
            ).fetchone()
            if row is None:  # pragma: no cover - integrity error from another column
                raise
            if row["subject_id"] != run.subject_id:
                raise PermissionDenied("not permitted") from None
            return _decode_run(row)
        return None

    def finish_run(self, run: QueryRun) -> None:
        self._conn.execute(
            "UPDATE runs SET status=?, sql=?, columns=?, rows=?, truncated=?, error=? "
            "WHERE run_id=?",
            (
                run.status.value,
                run.sql,
                json.dumps(list(run.columns), ensure_ascii=False),
                json.dumps([list(row) for row in run.rows], ensure_ascii=False, default=str),
                int(run.truncated),
                run.error,
                run.run_id,
            ),
        )

    def get_run(self, subject_id: str, run_id: str) -> QueryRun:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise NotFound(f"no such run: {run_id}")
        if row["subject_id"] != subject_id:
            raise PermissionDenied("not permitted")
        return _decode_run(row)


def _encode_definition(definition: BusinessDefinition) -> str:
    return json.dumps(
        {
            "metric": definition.metric,
            "display_name": definition.display_name,
            "rules": [
                {
                    "key": r.key,
                    "value": r.value,
                    "source": r.source.value,
                    "evidence_ref": r.evidence_ref,
                    "note": r.note,
                }
                for r in definition.rules
            ],
            "missing": list(definition.missing),
            "candidates": [
                {
                    "key": c.key,
                    "label": c.label,
                    "summary": c.summary,
                    "evidence_ref": c.evidence_ref,
                }
                for c in definition.candidates
            ],
        },
        ensure_ascii=False,
    )


def _decode_definition(text: str) -> BusinessDefinition:
    raw = json.loads(text)
    return BusinessDefinition(
        metric=raw["metric"],
        display_name=raw["display_name"],
        rules=tuple(
            Rule(
                key=r["key"],
                value=r["value"],
                source=RuleSource(r["source"]),
                evidence_ref=r["evidence_ref"],
                note=r["note"],
            )
            for r in raw["rules"]
        ),
        missing=tuple(raw["missing"]),
        candidates=tuple(Candidate(**c) for c in raw["candidates"]),
    )


def _decode_draft(row: sqlite3.Row) -> DefinitionDraft:
    return DefinitionDraft(
        draft_id=row["draft_id"],
        request_id=row["request_id"],
        subject_id=row["subject_id"],
        workspace_id=row["workspace_id"],
        question=row["question"],
        version=row["version"],
        status=DraftStatus(row["status"]),
        definition=_decode_definition(row["definition"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _decode_run(row: sqlite3.Row) -> QueryRun:
    return QueryRun(
        run_id=row["run_id"],
        draft_id=row["draft_id"],
        confirmation_id=row["confirmation_id"],
        subject_id=row["subject_id"],
        idempotency_key=row["idempotency_key"],
        status=RunStatus(row["status"]),
        sql=row["sql"],
        columns=tuple(json.loads(row["columns"])),
        rows=tuple(tuple(r) for r in json.loads(row["rows"])),
        truncated=bool(row["truncated"]),
        error=row["error"],
    )
