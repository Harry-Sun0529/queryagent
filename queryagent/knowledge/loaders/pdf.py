"""PDF loader — optional extra: ``pip install -e ".[docs]"``.

Imported lazily by ``load_document`` so the base install never needs pypdf.

Text-extractable PDFs only. A scanned page yields no text layer, and this
loader says so rather than returning an empty document: silence about a
rule and a page we could not read are different claims (K8). OCR is not
promised (D20).
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from queryagent.knowledge.errors import DocumentParseError
from queryagent.knowledge.models import Block, Document, hash_text


def load_pdf(path: Path, *, doc_id: str) -> Document:
    """Parse a text-extractable PDF, one block per non-empty page."""
    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001 - pypdf raises a wide range
        raise DocumentParseError(f"{path} could not be read as a PDF: {exc}") from exc

    blocks = tuple(
        Block(text.strip(), (), number, "page")
        for number, text in enumerate(pages, start=1)
        if text.strip()
    )
    if pages and not blocks:
        raise DocumentParseError(
            f"{path} has {len(pages)} page(s) but no extractable text; it is "
            "probably a scan. OCR is not provided, so this document is not indexed."
        )
    return Document(
        doc_id=doc_id,
        path=str(path),
        title=path.stem,
        blocks=blocks,
        content_hash=hash_text("\n".join(block.text for block in blocks)),
    )
