"""DOCX loader over ``zipfile`` + ``ElementTree`` — no python-docx.

A .docx is a zip whose ``word/document.xml`` holds the text. Reading it with
the standard library is about forty lines and keeps the core install free of
another pinned dependency, which is the stated position of this project
(spec §四, ADR-001's reasoning applied to parsing rather than agents).

The one non-obvious part is run fragmentation: Word splits a sentence across
``<w:r>`` elements at arbitrary points — a spell-check pass alone will do it
— so paragraph text must be rejoined before anything can match a quote
against it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

from queryagent.knowledge.errors import DocumentParseError
from queryagent.knowledge.models import Block, Document, hash_text

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DOCUMENT_PART = "word/document.xml"

# Word writes localised style ids ("Heading1", "berschrift1", "1"),
# so the level is taken from the trailing digit rather than the name.
_HEADING_PREFIXES = ("heading", "titre", "berschrift", "")


def load_docx(path: Path, *, doc_id: str) -> Document:
    """Parse a .docx into positioned paragraphs."""
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read(_DOCUMENT_PART)
    except zipfile.BadZipFile as exc:
        raise DocumentParseError(f"{path} is not a readable .docx archive: {exc}") from exc
    except KeyError as exc:
        raise DocumentParseError(
            f"{path} has no {_DOCUMENT_PART}; it may be an unsupported Word format"
        ) from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise DocumentParseError(f"{path}: {_DOCUMENT_PART} is not valid XML: {exc}") from exc

    blocks: list[Block] = []
    section: list[str] = []
    title = ""
    for number, paragraph in enumerate(root.iter(f"{_W}p"), start=1):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_W}t")).strip()
        if not text:
            continue
        level = _heading_level(paragraph)
        if level is not None:
            del section[level - 1 :]
            section.append(text)
            title = title or text
            blocks.append(Block(text, tuple(section), number, "paragraph", is_heading=True))
            continue
        blocks.append(Block(text, tuple(section), number, "paragraph"))
    return Document(
        doc_id=doc_id,
        path=str(path),
        title=title,
        blocks=tuple(blocks),
        content_hash=hash_text("\n".join(block.text for block in blocks)),
    )


def _heading_level(paragraph: ElementTree.Element) -> int | None:
    """Heading depth from the paragraph style, or None for body text."""
    style = paragraph.find(f"{_W}pPr/{_W}pStyle")
    if style is None:
        return None
    name = (style.get(f"{_W}val") or "").lower()
    if not name or not name[-1].isdigit():
        return None
    if not any(name.startswith(prefix) for prefix in _HEADING_PREFIXES if prefix):
        return None
    return int(name[-1])
