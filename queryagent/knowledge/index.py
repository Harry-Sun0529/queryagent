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
from queryagent.sqlite_state import open_shared
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
        self.removed = 0
        """Chunks dropped because their file or section is no longer there."""

    def render(self) -> str:
        lines = [f"已纳入 {len(self.imported)} 个文件："]
        lines.extend(f"  · {path}" for path in self.imported)
        if self.removed:
            lines.append(
                f"已移除 {self.removed} 个片段：它们的文件或章节已不在该目录下，"
                "引用它们的确认单会失效"
            )
        if self.skipped:
            lines.append(f"未能纳入 {len(self.skipped)} 个文件（其规则不会出现在任何草案里）：")
            lines.extend(f"  · {path} — {why}" for path, why in self.skipped)
        return "\n".join(lines)


class SqliteKnowledgeIndex:
    """Document chunks, scoped by workspace."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._conn = open_shared(self._path, _SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # --------------------------------------------------------------- import

    def import_directory(self, directory: str | Path, *, workspace_id: str) -> ImportReport:
        """Index every supported file under ``directory`` into one workspace.

        Re-importing is idempotent for unchanged content: chunk ids are
        derived from the document and section, so a stored citation survives
        a re-index (§4.5.4), and a chunk whose text did not change keeps its
        vector.

        The index follows the directory, not only into it. A file deleted
        from the directory, or a section deleted from a file, is deleted
        here too: found in the 1.1 read-through, an import only ever added,
        so a withdrawn handbook went on supplying rules and its citations
        went on checking out. A file that could not be read this time keeps
        what it had; it is reported as skipped, and a parse failure must not
        look like the document being withdrawn.

        One file belongs to one workspace. Chunk ids come from the path, so
        the same file under a second workspace would take the first one's
        chunks away; it is skipped and reported instead.
        """
        report = ImportReport()
        root = Path(directory)
        kept: set[str] = set()
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            try:
                document = load_document(path)
            except (DocumentParseError, UnsupportedFormat) as exc:
                report.skipped.append((str(path), str(exc)))
                kept.add(str(path))
                continue
            elsewhere = self._conn.execute(
                "SELECT workspace_id FROM chunks WHERE doc_id = ? AND workspace_id != ? LIMIT 1",
                (document.doc_id, workspace_id),
            ).fetchone()
            if elsewhere is not None:
                report.skipped.append(
                    (
                        str(path),
                        f"该文件已在业务空间 '{elsewhere['workspace_id']}' 的索引里；"
                        "一个文件只能属于一个业务空间",
                    )
                )
                continue
            chunks = chunk_document(document)
            self._upsert(chunks, document, workspace_id)
            report.removed += self._drop_sections_gone(document, chunks, workspace_id)
            report.imported.append(str(path))
            kept.add(str(path))
        report.removed += self._drop_files_gone(root, kept, workspace_id)
        return report

    def _drop_sections_gone(
        self, document: Document, chunks: tuple[Chunk, ...], workspace_id: str
    ) -> int:
        """Delete this document's chunks that the file no longer produces."""
        current = {chunk.chunk_id for chunk in chunks}
        stored = self._conn.execute(
            "SELECT chunk_id FROM chunks WHERE doc_id = ? AND workspace_id = ?",
            (document.doc_id, workspace_id),
        ).fetchall()
        gone = [(row["chunk_id"],) for row in stored if row["chunk_id"] not in current]
        self._conn.executemany("DELETE FROM chunks WHERE chunk_id = ?", gone)
        return len(gone)

    def _drop_files_gone(self, root: Path, kept: set[str], workspace_id: str) -> int:
        """Delete chunks of files that were under ``root`` and are not any more.

        Only this directory's files: another source of the same workspace is
        not this import's to judge.
        """
        prefix = str(root).rstrip("/") + "/"
        stored = self._conn.execute(
            "SELECT DISTINCT doc_path FROM chunks WHERE workspace_id = ?", (workspace_id,)
        ).fetchall()
        removed = 0
        for row in stored:
            doc_path = row["doc_path"]
            if doc_path.startswith(prefix) and doc_path not in kept:
                removed += self._conn.execute(
                    "DELETE FROM chunks WHERE workspace_id = ? AND doc_path = ?",
                    (workspace_id, doc_path),
                ).rowcount
        return removed

    def _upsert(
        self, chunks: tuple[Chunk, ...], document: Document, workspace_id: str
    ) -> None:
        self._conn.executemany(
            # The vector survives only while the text it was made from does.
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(chunk_id) DO UPDATE SET doc_id = excluded.doc_id, "
            "doc_path = excluded.doc_path, doc_title = excluded.doc_title, "
            "workspace_id = excluded.workspace_id, text = excluded.text, "
            "section_path = excluded.section_path, start = excluded.start, "
            '"end" = excluded."end", unit = excluded.unit, terms = excluded.terms, '
            "vector = CASE WHEN chunks.content_hash = excluded.content_hash "
            "THEN chunks.vector ELSE '' END, content_hash = excluded.content_hash",
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
