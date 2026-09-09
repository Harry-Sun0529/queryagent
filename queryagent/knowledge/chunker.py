"""Grouping parsed blocks into citable chunks.

The chunking decision that matters is not size, it is *where the cuts go*.
A business rule and the sentence that qualifies it ("…不含测试账号") must
land in the same chunk, or retrieval can surface the rule without its
condition — which is the single most damaging failure this layer can have,
because the result looks perfectly well-cited.

Section boundaries are used because the author already decided there that
one rule ends and the next begins. A token-count window would cut in the
middle of that decision.
"""

from __future__ import annotations

import hashlib

from queryagent.knowledge.models import Block, Chunk, Document, hash_text
from queryagent.text import normalize


def chunk_document(document: Document) -> tuple[Chunk, ...]:
    """Split a parsed document into one chunk per non-empty section."""
    chunks: list[Chunk] = []
    current: list[Block] = []

    def flush() -> None:
        if not current:
            return
        chunk = _build(document, tuple(current))
        if chunk is not None:
            chunks.append(chunk)
        current.clear()

    for block in document.blocks:
        if block.is_heading:
            flush()
        current.append(block)
    flush()
    return tuple(chunks)


def _build(document: Document, blocks: tuple[Block, ...]) -> Chunk | None:
    """Assemble one chunk, or None when the section has no body.

    The heading is kept in the chunk text rather than only in
    ``section_path``: retrieved on its own, 「按 first_order_at 计数」 does
    not say what is being counted, and the model would be reading a rule
    stripped of its subject.
    """
    body = [block for block in blocks if not block.is_heading]
    if not body:
        return None
    text = _join(blocks)
    section_path = blocks[0].section_path
    return Chunk(
        chunk_id=_chunk_id(document.doc_id, section_path, blocks[0].position),
        doc_id=document.doc_id,
        text=text,
        section_path=section_path,
        start=blocks[0].position,
        end=blocks[-1].position,
        unit=blocks[0].unit,
        content_hash=hash_text(text),
    )


def _join(blocks: tuple[Block, ...]) -> str:
    """Render a section as one normalised line, heading first.

    The heading is separated by a colon rather than whitespace. Normalisation
    folds a newline between two CJK characters away entirely — correct for a
    sentence broken mid-way by DOCX extraction, wrong here, where it welds
    「新增用户口径」 onto 「运营口径按…」 into a run-on that is both unreadable
    as displayed quote context and a source of substrings present in no
    document. A colon is content, so it survives.
    """
    heading = [block.text for block in blocks if block.is_heading]
    body = " ".join(block.text for block in blocks if not block.is_heading)
    return normalize(f"{heading[0]}：{body}" if heading else body)


def _chunk_id(doc_id: str, section_path: tuple[str, ...], position: int) -> str:
    """Stable id: a citation stored today must resolve tomorrow (§4.5.4).

    Derived from the document and the section rather than an ordinal, so
    inserting a section earlier in the file does not renumber every citation
    after it. The starting position is included because a document may
    legitimately repeat a heading.
    """
    seed = f"{doc_id}\x00{'>'.join(section_path)}\x00{position}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
