"""Value objects for parsed documents.

Positions are kept per block rather than only per document because a
citation has to point somewhere a person can open and check — a file name
alone is not evidence, it is an assertion (D01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    """One parsed unit of a document, before chunking.

    Attributes:
        text: The unit's text, already joined across any source fragments.
        section_path: Heading breadcrumb this unit sits under, outermost
            first. Empty before the first heading.
        position: 1-based index in the unit's own coordinate system.
        unit: What ``position`` counts — "line", "paragraph" or "page".
            Different formats can only offer different granularity, and
            pretending otherwise would make citations point at nothing.
        is_heading: Headings are kept as blocks so a chunk can carry the
            wording of the section it came from.
    """

    text: str
    section_path: tuple[str, ...]
    position: int
    unit: str
    is_heading: bool = False


@dataclass(frozen=True)
class Document:
    """A parsed source file.

    ``content_hash`` is over the parsed text, not the raw bytes: re-saving a
    .docx changes its zip container on every write, and a change detector
    that fires on that would expire confirmations for nothing (§4.5.6).
    """

    doc_id: str
    path: str
    title: str
    blocks: tuple[Block, ...]
    content_hash: str


@dataclass(frozen=True)
class Chunk:
    """The unit a rule cites.

    Boundaries follow document sections rather than a token count. A chunk
    that straddles a rule boundary makes a citation unresolvable — the
    reader cannot tell which half was meant — and one that cuts a rule away
    from its qualifying sentence changes what the rule says. Section edges
    are where the author already decided one rule ends.

    ``text`` is stored normalised: quote offsets are computed against it, so
    the stored form has to be the compared form (see ``queryagent.text``).

    ``start``/``end`` are inclusive positions in ``unit`` coordinates, so a
    citation can name a line, paragraph or page range a person can open.
    """

    chunk_id: str
    doc_id: str
    text: str
    section_path: tuple[str, ...]
    start: int
    end: int
    unit: str
    content_hash: str


def hash_text(text: str) -> str:
    """Stable content hash used for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
