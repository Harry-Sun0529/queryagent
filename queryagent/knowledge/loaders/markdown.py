"""Markdown loader (stdlib only).

Deliberately not a full Markdown parser. What the evidence layer needs from
a document is the heading breadcrumb and a line a person can open to — not a
rendered tree. A dependency that produced an AST would give us more than we
use and one more thing to keep pinned.
"""

from __future__ import annotations

import re
from pathlib import Path

from queryagent.knowledge.models import Block, Document, hash_text

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def load_markdown(path: Path, *, doc_id: str) -> Document:
    """Parse a Markdown file into positioned blocks."""
    text = path.read_text(encoding="utf-8")
    blocks: list[Block] = []
    section: list[str] = []
    title = ""
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        heading = _ATX_HEADING.match(stripped)
        if heading is not None:
            level = len(heading.group(1))
            name = heading.group(2)
            # Truncate to the parent level, then descend — a jump from H1 to
            # H3 keeps the breadcrumb short rather than inventing a level.
            del section[level - 1 :]
            section.append(name)
            title = title or name
            blocks.append(Block(name, tuple(section), number, "line", is_heading=True))
            continue
        blocks.append(Block(stripped, tuple(section), number, "line"))
    return Document(
        doc_id=doc_id,
        path=str(path),
        title=title,
        blocks=tuple(blocks),
        content_hash=hash_text("\n".join(block.text for block in blocks)),
    )
