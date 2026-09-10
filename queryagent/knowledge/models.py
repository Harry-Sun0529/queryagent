"""Value objects for parsed documents.

Positions are kept per block rather than only per document because a
citation has to point somewhere a person can open and check — a file name
alone is not evidence, it is an assertion (D01).
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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


class RefStatus(Enum):
    """Whether a stored citation still stands (§4.5.6).

    Revoked and deleted both report ``UNAVAILABLE``: telling them apart tells
    the caller that a chunk they cannot read exists, which is the disclosure
    the workspace boundary was drawn to prevent.
    """

    OK = "ok"
    CHANGED = "changed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class EvidenceRef:
    """A citation, in its stable form.

    Deliberately carries no document version. Putting one here would push it
    into ``BusinessDefinition.content_hash`` — and then fixing a typo in a
    handbook would invalidate every confirmation that cited it. Users facing
    constant re-confirmation stop reading what they confirm, so the net
    effect of that "stricter" design is less safety, not more.

    Whether the cited text still says what it said is a different question,
    answered by ``KnowledgeProvider.check_refs`` (§4.5.4).
    """

    doc_id: str
    chunk_id: str
    quote_start: int = 0
    quote_end: int = 0
    content_hash: str = ""
    """The chunk's content when this citation was made.

    Carried on the object but **excluded from** :meth:`render`, which is what
    goes into ``Rule.evidence_ref`` and therefore into the definition hash.
    That split is the whole point: change detection needs to know what the
    text said, while the confirmation must not be invalidated by an edit
    that did not change the rule the user approved.
    """

    def replace(self, **changes: object) -> EvidenceRef:
        """A copy with fields replaced — used by tests and revocation paths."""
        return dataclasses.replace(self, **changes)  # type: ignore[arg-type]

    def render(self) -> str:
        """The stable string stored in ``Rule.evidence_ref``.

        Version-free by construction (§4.5.4).
        """
        return f"{self.doc_id}#{self.chunk_id}@{self.quote_start}:{self.quote_end}"

    @classmethod
    def parse(cls, rendered: str) -> EvidenceRef:
        """Inverse of :meth:`render`; offsets that are not numbers read as 0."""
        body, _, span = rendered.partition("@")
        doc_id, _, chunk_id = body.partition("#")
        start, _, end = span.partition(":")
        return cls(
            doc_id=doc_id,
            chunk_id=chunk_id,
            quote_start=int(start) if start.isdigit() else 0,
            quote_end=int(end) if end.isdigit() else 0,
        )


@dataclass(frozen=True)
class IndexedChunk:
    """A chunk as the index holds it: content plus where it may be seen."""

    chunk_id: str
    doc_id: str
    doc_path: str
    doc_title: str
    workspace_id: str
    text: str
    section_path: tuple[str, ...]
    start: int
    end: int
    unit: str
    content_hash: str

    def citation(self) -> str:
        """Human-facing location: the thing a person can open and check."""
        where = f"{self.start}" if self.start == self.end else f"{self.start}-{self.end}"
        section = " › ".join(self.section_path)
        parts = [Path(self.doc_path).name]
        if section:
            parts.append(section)
        parts.append(f"{self.unit} {where}")
        return " · ".join(parts)


@dataclass(frozen=True)
class Evidence:
    """An authorised chunk, re-read at the moment it is needed."""

    ref: EvidenceRef
    chunk: IndexedChunk


@dataclass(frozen=True)
class EvidenceHit:
    """A search result: the chunk, its ref, and why it ranked."""

    ref: EvidenceRef
    chunk: IndexedChunk
    score: float


def hash_text(text: str) -> str:
    """Stable content hash used for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
