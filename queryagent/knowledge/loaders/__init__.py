"""Format dispatch for document loading.

Same shape as ``connectors.make_connector``: an explicit branch per format,
with the optional one imported lazily so the base install never needs its
driver. PDF is an extra (``pip install -e ".[docs]"``) because ``pypdf`` is
a real dependency for a format not everyone has.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from queryagent.knowledge.errors import UnsupportedFormat
from queryagent.knowledge.models import Document

SUPPORTED_SUFFIXES = (".md", ".markdown", ".docx", ".pdf")


def load_document(path: str | Path, *, doc_id: str | None = None) -> Document:
    """Parse one file into a :class:`Document`.

    Args:
        path: The file to read.
        doc_id: Stable identifier; defaults to a hash of the path, so the
            same file keeps its id across runs and a moved file gets a new
            one (a moved file may well have moved between workspaces).

    Raises:
        FileNotFoundError: The path does not exist.
        UnsupportedFormat: The suffix is not one this build reads.
        DocumentParseError: The file was recognised but could not be read.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no such document: {path}")
    identifier = doc_id or hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown"):
        from queryagent.knowledge.loaders.markdown import load_markdown

        return load_markdown(path, doc_id=identifier)
    if suffix == ".docx":
        from queryagent.knowledge.loaders.docx import load_docx

        return load_docx(path, doc_id=identifier)
    if suffix == ".pdf":
        # Lazy: pypdf is an optional extra (pip install -e ".[docs]").
        from queryagent.knowledge.loaders.pdf import load_pdf

        return load_pdf(path, doc_id=identifier)
    raise UnsupportedFormat(
        f"cannot read '{suffix or path.name}': supported formats are "
        f"{', '.join(SUPPORTED_SUFFIXES)}. Scanned PDFs need OCR, which this "
        "release does not provide."
    )
