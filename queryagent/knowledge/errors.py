"""Knowledge-layer errors.

``DocumentParseError`` exists to keep one distinction the product depends
on: *we could not read this file* is not the same claim as *this file does
not mention the rule*. The second is a statement about the business, and a
parser failure must never be rendered as one (D20, K8).
"""

from __future__ import annotations

from queryagent.errors import QueryAgentError


class KnowledgeError(QueryAgentError):
    """Base class for document-evidence failures."""


class DocumentParseError(KnowledgeError):
    """A file was recognised but could not be read.

    Always names the file: the operator has to know which document is
    missing from the index, because its rules are silently absent until it
    is fixed.
    """


class UnsupportedFormat(KnowledgeError):
    """The file's extension is not one this build can read.

    Distinct from a parse error: nothing is broken, the format was simply
    never claimed. Scanned PDFs and OCR are explicitly not promised.
    """


class EvidenceUnavailable(KnowledgeError):
    """The citation cannot be read by this subject, right now.

    One error for revoked, deleted and never-authorised on purpose, with one
    message. A caller that can tell "you may not read this" from "this does
    not exist" has learned that it exists.
    """
