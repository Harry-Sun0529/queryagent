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
from typing import NamedTuple

from queryagent.workflow.errors import NotFound, PermissionDenied, StaleVersion
from queryagent.workflow.models import (
    HUMAN_CHANNELS,
    BusinessDefinition,
    Candidate,
    Channel,
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
CREATE TABLE IF NOT EXISTS draft_evidence (
    draft_id TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    PRIMARY KEY (draft_id, evidence_ref)
);
CREATE TABLE IF NOT EXISTS confirmations (
    confirmation_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    draft_version INTEGER NOT NULL,
    definition_hash TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'cli'
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL,
    confirmation_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    sql TEXT NOT NULL DEFAULT '',
    params TEXT NOT NULL DEFAULT '[]',
    columns TEXT NOT NULL DEFAULT '[]',
    rows TEXT NOT NULL DEFAULT '[]',
    truncated INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    freshness_sql TEXT NOT NULL DEFAULT '',
    data_through TEXT NOT NULL DEFAULT '',
    expected_through TEXT NOT NULL DEFAULT '',
    mapping_fingerprint TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS freshness_cache (
    source TEXT NOT NULL,
    time_column TEXT NOT NULL,
    latest TEXT NOT NULL,
    probed_at TEXT NOT NULL,
    PRIMARY KEY (source, time_column)
);
"""

# Columns added to a table after its first release, with their declarations.
_LATER_COLUMNS = {
    "runs": (
        ("params", "TEXT NOT NULL DEFAULT '[]'"),
        ("freshness_sql", "TEXT NOT NULL DEFAULT ''"),
        ("data_through", "TEXT NOT NULL DEFAULT ''"),
        ("expected_through", "TEXT NOT NULL DEFAULT ''"),
        ("mapping_fingerprint", "TEXT NOT NULL DEFAULT ''"),
    ),
    # Every confirmation before 1.0 came from the terminal: the default is
    # what those rows were, not a guess (H9).
    "confirmations": (("channel", "TEXT NOT NULL DEFAULT 'cli'"),),
}


class ConfirmedRun(NamedTuple):
    """A definition as it was confirmed, and what ran it (T42)."""

    definition: BusinessDefinition
    confirmed_at: datetime
    mapping_fingerprint: str


class CachedProbe(NamedTuple):
    """The last freshness probe of one table taken before a confirmation (T41)."""

    latest: str
    probed_at: datetime


class SqliteWorkflowStore:
    """Durable state for the workflow layer."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        """Bring a state file written by an earlier version up to this schema.

        ``CREATE TABLE IF NOT EXISTS`` leaves an existing table alone, so a
        column added later has to be added here — or the first run recorded
        after an upgrade fails on a state file that was working yesterday.
        """
        for table, columns in _LATER_COLUMNS.items():
            present = {
                row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")
            }
            for column, declaration in columns:
                if column not in present:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

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

    def expire_draft(self, subject_id: str, draft_id: str) -> None:
        """Mark a draft's evidence no longer valid.

        Status only: version and content hash stay put. Bumping the version
        would make ``execute``'s version check fire first and report "the
        口径 changed" for what is actually "the evidence is gone" — two
        different things for the user to do about (§4.5.6).
        """
        self.get_draft(subject_id, draft_id)  # ownership first
        self._conn.execute(
            "UPDATE drafts SET status = ? WHERE draft_id = ?",
            (DraftStatus.EXPIRED.value, draft_id),
        )

    def set_evidence(self, subject_id: str, draft_id: str, refs: tuple[str, ...]) -> None:
        """Record which citations a draft rests on."""
        self.get_draft(subject_id, draft_id)
        self._conn.execute("DELETE FROM draft_evidence WHERE draft_id = ?", (draft_id,))
        self._conn.executemany(
            "INSERT OR REPLACE INTO draft_evidence VALUES (?,?)",
            [(draft_id, ref) for ref in refs],
        )

    def evidence_of(self, subject_id: str, draft_id: str) -> tuple[str, ...]:
        """The citations a draft rests on, for re-checking before it is used."""
        self.get_draft(subject_id, draft_id)
        rows = self._conn.execute(
            "SELECT evidence_ref FROM draft_evidence WHERE draft_id = ? ORDER BY evidence_ref",
            (draft_id,),
        ).fetchall()
        return tuple(row["evidence_ref"] for row in rows)

    def pending_drafts(
        self, subject_id: str, workspace_id: str, *, limit: int = 50
    ) -> tuple[DefinitionDraft, ...]:
        """Drafts still waiting on this person, newest first (T45).

        Waiting means open for input, or complete with no confirmation of its
        current version and hash. Expired drafts are not waiting on anyone.
        """
        rows = self._conn.execute(
            "SELECT d.* FROM drafts d LEFT JOIN confirmations c ON c.draft_id = d.draft_id "
            "AND c.draft_version = d.version AND c.definition_hash = d.definition_hash "
            "WHERE d.subject_id = ? AND d.workspace_id = ? AND d.status IN (?, ?) "
            "AND c.confirmation_id IS NULL ORDER BY d.updated_at DESC LIMIT ?",
            (
                subject_id,
                workspace_id,
                DraftStatus.NEEDS_INPUT.value,
                DraftStatus.AWAITING_CONFIRMATION.value,
                limit,
            ),
        ).fetchall()
        return tuple(_decode_draft(row) for row in rows)

    def draft_ids_starting(self, subject_id: str, prefix: str) -> tuple[str, ...]:
        """This subject's draft ids beginning with ``prefix``: the sheet shows eight characters."""
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = self._conn.execute(
            "SELECT draft_id FROM drafts WHERE subject_id = ? AND draft_id LIKE ? ESCAPE '\\' "
            "ORDER BY draft_id",
            (subject_id, escaped + "%"),
        ).fetchall()
        return tuple(row["draft_id"] for row in rows)

    # --------------------------------------------------------- confirmations

    def save_confirmation(self, confirmation: Confirmation) -> None:
        self._conn.execute(
            "INSERT INTO confirmations (confirmation_id, draft_id, draft_version, "
            "definition_hash, subject_id, confirmed_at, channel) VALUES (?,?,?,?,?,?,?)",
            (
                confirmation.confirmation_id,
                confirmation.draft_id,
                confirmation.draft_version,
                confirmation.definition_hash,
                confirmation.subject_id,
                confirmation.confirmed_at.isoformat(),
                confirmation.channel.value,
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
        return _decode_confirmation(row)

    def human_confirmation(
        self, subject_id: str, draft_id: str, version: int, definition_hash: str
    ) -> Confirmation | None:
        """The newest confirmation a person gave this exact version, or None (T44).

        Filtered on the channel as well as the version and hash. No code path
        writes an agent's confirmation, and this read would not accept one if
        a future one did (ADR-013).
        """
        self.get_draft(subject_id, draft_id)  # ownership first
        row = self._conn.execute(
            "SELECT * FROM confirmations WHERE draft_id = ? AND subject_id = ? "
            "AND draft_version = ? AND definition_hash = ? AND channel IN ("
            + ",".join("?" for _ in HUMAN_CHANNELS)
            + ") ORDER BY confirmed_at DESC LIMIT 1",
            (
                draft_id,
                subject_id,
                version,
                definition_hash,
                *(channel.value for channel in HUMAN_CHANNELS),
            ),
        ).fetchone()
        return _decode_confirmation(row) if row is not None else None

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
            "UPDATE runs SET status=?, sql=?, params=?, columns=?, rows=?, truncated=?, error=?, "
            "freshness_sql=?, data_through=?, expected_through=?, mapping_fingerprint=? "
            "WHERE run_id=?",
            (
                run.status.value,
                run.sql,
                json.dumps(list(run.params), ensure_ascii=False),
                json.dumps(list(run.columns), ensure_ascii=False),
                json.dumps([list(row) for row in run.rows], ensure_ascii=False, default=str),
                int(run.truncated),
                run.error,
                run.freshness_sql,
                run.data_through,
                run.expected_through,
                run.mapping_fingerprint,
                run.run_id,
            ),
        )

    def get_run_by_key(self, subject_id: str, idempotency_key: str) -> QueryRun | None:
        """The run holding this key, or None when it was never claimed."""
        row = self._conn.execute(
            "SELECT * FROM runs WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        if row is None:
            return None
        if row["subject_id"] != subject_id:
            raise PermissionDenied("not permitted")
        return _decode_run(row)

    def get_run(self, subject_id: str, run_id: str) -> QueryRun:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise NotFound(f"no such run: {run_id}")
        if row["subject_id"] != subject_id:
            raise PermissionDenied("not permitted")
        return _decode_run(row)

    def latest_run_of(self, subject_id: str, confirmation_id: str) -> QueryRun | None:
        """The newest run against one confirmation, whoever's key it holds, or None."""
        row = self._conn.execute(
            "SELECT * FROM runs WHERE confirmation_id = ? AND subject_id = ? "
            "ORDER BY rowid DESC LIMIT 1",
            (confirmation_id, subject_id),
        ).fetchone()
        return _decode_run(row) if row is not None else None

    # --------------------------------------------------------------- history

    def last_confirmed(
        self, subject_id: str, workspace_id: str, metric: str, since: datetime
    ) -> ConfirmedRun | None:
        """The newest definition this subject confirmed and ran for ``metric`` (T42).

        Derived, not kept in a table of its own: a confirmation and a
        successful run are the record. Only a draft still at the version that
        was confirmed counts — one amended after its run no longer holds what
        was approved. Returns the definition, when it was confirmed, and the
        fingerprint of the mapping that ran.
        """
        rows = self._conn.execute(
            "SELECT d.version, d.definition_hash, d.definition, c.draft_version, "
            "c.definition_hash AS confirmed_hash, c.confirmed_at, r.mapping_fingerprint "
            "FROM runs r JOIN confirmations c ON c.confirmation_id = r.confirmation_id "
            "JOIN drafts d ON d.draft_id = r.draft_id "
            "WHERE r.subject_id = ? AND d.subject_id = ? AND d.workspace_id = ? "
            "AND r.status = ? ORDER BY c.confirmed_at DESC",
            (subject_id, subject_id, workspace_id, RunStatus.SUCCEEDED.value),
        ).fetchall()
        for row in rows:
            confirmed_at = datetime.fromisoformat(row["confirmed_at"])
            if confirmed_at < since:
                return None
            if (row["version"], row["definition_hash"]) != (
                row["draft_version"],
                row["confirmed_hash"],
            ):
                continue
            definition = _decode_definition(row["definition"])
            if definition.metric == metric:
                return ConfirmedRun(definition, confirmed_at, row["mapping_fingerprint"])
        return None

    # ------------------------------------------------------------- freshness

    def cached_freshness(self, source: str, time_column: str) -> CachedProbe | None:
        """The last probe's answer for one table, and when it was read (T41).

        Not scoped by subject: the newest record's date in a table is the
        same answer for everyone who may query it.
        """
        row = self._conn.execute(
            "SELECT latest, probed_at FROM freshness_cache WHERE source = ? AND time_column = ?",
            (source, time_column),
        ).fetchone()
        if row is None:
            return None
        return CachedProbe(row["latest"], datetime.fromisoformat(row["probed_at"]))

    def cache_freshness(
        self, source: str, time_column: str, latest: str, probed_at: datetime
    ) -> None:
        self._conn.execute(
            "INSERT INTO freshness_cache VALUES (?,?,?,?) ON CONFLICT(source, time_column) "
            "DO UPDATE SET latest = excluded.latest, probed_at = excluded.probed_at",
            (source, time_column, latest, probed_at.isoformat()),
        )


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
                    **_implies_field(r.implies),
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
                    **_implies_field(c.implies),
                }
                for c in definition.candidates
            ],
        },
        ensure_ascii=False,
    )


def _implies_field(implies: tuple[str, ...]) -> dict[str, list[str]]:
    """Written only when present, so a v0.7 reader — which builds candidates
    with ``Candidate(**c)`` — can still open every draft that uses no T39
    correspondence."""
    return {"implies": list(implies)} if implies else {}


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
                implies=tuple(r.get("implies", ())),
            )
            for r in raw["rules"]
        ),
        missing=tuple(raw["missing"]),
        # Drafts written before T39 have no "implies"; they read as none.
        candidates=tuple(
            Candidate(
                key=c["key"],
                label=c["label"],
                summary=c["summary"],
                evidence_ref=c["evidence_ref"],
                implies=tuple(c.get("implies", ())),
            )
            for c in raw["candidates"]
        ),
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


def _decode_confirmation(row: sqlite3.Row) -> Confirmation:
    return Confirmation(
        confirmation_id=row["confirmation_id"],
        draft_id=row["draft_id"],
        draft_version=row["draft_version"],
        definition_hash=row["definition_hash"],
        subject_id=row["subject_id"],
        confirmed_at=datetime.fromisoformat(row["confirmed_at"]),
        channel=Channel(row["channel"]),
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
        params=tuple(json.loads(row["params"])),
        columns=tuple(json.loads(row["columns"])),
        rows=tuple(tuple(r) for r in json.loads(row["rows"])),
        truncated=bool(row["truncated"]),
        error=row["error"],
        freshness_sql=row["freshness_sql"],
        data_through=row["data_through"],
        expected_through=row["expected_through"],
        mapping_fingerprint=row["mapping_fingerprint"],
    )
