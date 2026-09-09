"""SQLite index over imported documents.

Same shape as ``workflow/store.py``: one local file, WAL, no service. The
important property is not storage, it is that **the workspace is part of the
query**. A search that fetched candidates and filtered afterwards would have
already loaded another workspace's text into the process that builds the
model's prompt; filtering it out later does not undo that (§10.4, K3).

Scope boundary: one process, one file. Multi-replica deployment needs shared
coordination before any claim here holds.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from queryagent.knowledge.chunker import chunk_document
from queryagent.knowledge.embedding import EmbeddingClient
from queryagent.knowledge.errors import DocumentParseError, UnsupportedFormat
from queryagent.knowledge.loaders import SUPPORTED_SUFFIXES, load_document
from queryagent.knowledge.models import Chunk, Document, IndexedChunk
from queryagent.text import tokens

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    doc_path TEXT NOT NULL,
    doc_title TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    text TEXT NOT NULL,
    section_path TEXT NOT NULL,
    start INTEGER NOT NULL,
    end INTEGER NOT NULL,
    unit TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    terms TEXT NOT NULL,
    vector TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS chunks_by_workspace ON chunks (workspace_id);
"""


class ImportReport:
    """What an import actually took in — and what it could not read.

    Printed rather than summarised: a document missing from the index is a
    set of business rules silently absent from every future draft, and the
    operator is the only one who can notice.
    """

    def __init__(self) -> None:
        self.imported: list[str] = []
        self.skipped: list[tuple[str, str]] = []

    def render(self) -> str:
        lines = [f"已纳入 {len(self.imported)} 个文件："]
        lines.extend(f"  · {path}" for path in self.imported)
        if self.skipped:
            lines.append(f"未能纳入 {len(self.skipped)} 个文件（其规则不会出现在任何草案里）：")
            lines.extend(f"  · {path} — {why}" for path, why in self.skipped)
        return "\n".join(lines)


class SqliteKnowledgeIndex:
    """Document chunks, scoped by workspace."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # --------------------------------------------------------------- import

    def import_directory(self, directory: str | Path, *, workspace_id: str) -> ImportReport:
        """Index every supported file under ``directory`` into one workspace.

        Re-importing is idempotent for unchanged content: chunk ids are
        derived from the document and section, so a stored citation survives
        a re-index (§4.5.4).
        """
        report = ImportReport()
        root = Path(directory)
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            try:
                document = load_document(path)
            except (DocumentParseError, UnsupportedFormat) as exc:
                report.skipped.append((str(path), str(exc)))
                continue
            self._upsert(chunk_document(document), document, workspace_id)
            report.imported.append(str(path))
        return report

    def _upsert(
        self, chunks: tuple[Chunk, ...], document: Document, workspace_id: str
    ) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    chunk.chunk_id,
                    chunk.doc_id,
                    document.path,
                    document.title,
                    workspace_id,
                    chunk.text,
                    json.dumps(list(chunk.section_path), ensure_ascii=False),
                    chunk.start,
                    chunk.end,
                    chunk.unit,
                    chunk.content_hash,
                    json.dumps(sorted(tokens(chunk.text)), ensure_ascii=False),
                    "",
                )
                for chunk in chunks
            ],
        )

    def embed_missing(self, workspace_id: str, client: EmbeddingClient, *, batch: int = 32) -> int:
        """Embed chunks that have no vector yet; returns how many were added.

        Separate from import so a corpus can be indexed and searched with no
        embeddings endpoint at all, and so re-running never re-pays for
        chunks that already have one.
        """
        rows = self._conn.execute(
            "SELECT chunk_id, text FROM chunks WHERE workspace_id = ? AND vector = ''",
            (workspace_id,),
        ).fetchall()
        added = 0
        for start in range(0, len(rows), batch):
            window = rows[start : start + batch]
            vectors = client.embed([row["text"] for row in window])
            self._conn.executemany(
                "UPDATE chunks SET vector = ? WHERE chunk_id = ?",
                [
                    (json.dumps(vector), row["chunk_id"])
                    for row, vector in zip(window, vectors, strict=True)
                ],
            )
            added += len(window)
        return added

    def vectors_in(self, workspace_id: str) -> dict[str, list[float]]:
        """Stored vectors for one workspace. The workspace is in the WHERE."""
        rows = self._conn.execute(
            "SELECT chunk_id, vector FROM chunks WHERE workspace_id = ? AND vector != ''",
            (workspace_id,),
        ).fetchall()
        return {row["chunk_id"]: json.loads(row["vector"]) for row in rows}

    def revoke_workspace(self, workspace_id: str) -> None:
        """Drop a whole workspace — the local stand-in for access being withdrawn."""
        self._conn.execute("DELETE FROM chunks WHERE workspace_id = ?", (workspace_id,))

    # --------------------------------------------------------------- reading

    def chunks_in(self, workspace_id: str) -> tuple[IndexedChunk, ...]:
        """Every chunk visible to one workspace. The workspace is in the WHERE."""
        rows = self._conn.execute(
            "SELECT * FROM chunks WHERE workspace_id = ?", (workspace_id,)
        ).fetchall()
        return tuple(_decode(row) for row in rows)

    def get(self, workspace_id: str, chunk_id: str) -> IndexedChunk | None:
        """One chunk, or None — including when it exists in another workspace."""
        row = self._conn.execute(
            "SELECT * FROM chunks WHERE chunk_id = ? AND workspace_id = ?",
            (chunk_id, workspace_id),
        ).fetchone()
        return _decode(row) if row is not None else None

    def terms_of(self, workspace_id: str, chunk_id: str) -> frozenset[str]:
        row = self._conn.execute(
            "SELECT terms FROM chunks WHERE chunk_id = ? AND workspace_id = ?",
            (chunk_id, workspace_id),
        ).fetchone()
        return frozenset(json.loads(row["terms"])) if row is not None else frozenset()


def _decode(row: sqlite3.Row) -> IndexedChunk:
    return IndexedChunk(
        chunk_id=row["chunk_id"],
        doc_id=row["doc_id"],
        doc_path=row["doc_path"],
        doc_title=row["doc_title"],
        workspace_id=row["workspace_id"],
        text=row["text"],
        section_path=tuple(json.loads(row["section_path"])),
        start=row["start"],
        end=row["end"],
        unit=row["unit"],
        content_hash=row["content_hash"],
    )
