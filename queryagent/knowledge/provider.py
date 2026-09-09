"""Authorised retrieval over the local index.

The shape of this interface is the security design. Every method takes a
:class:`RetrievalScope`, and there is no overload without one — so "fetch
everything, then filter" is not something a caller *can* write. That matters
more than any check inside the implementation, because the next provider
(an enterprise knowledge base connector) will be written by someone reading
this Protocol rather than this file.

Permission has to hold before text is loaded, not before it is returned: a
chunk retrieved and then filtered has already been in the process that
builds the model's prompt (§10.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from queryagent.knowledge.embedding import EmbeddingClient, cosine
from queryagent.knowledge.errors import EvidenceUnavailable
from queryagent.knowledge.index import SqliteKnowledgeIndex
from queryagent.knowledge.models import Evidence, EvidenceHit, EvidenceRef, RefStatus
from queryagent.text import tokens
from queryagent.workflow.models import ActorContext

# One shared message for every refusal. Distinguishing "you may not read
# this" from "this does not exist" tells the caller that it exists.
_UNAVAILABLE = "引用不可用：文档已变更、被移除，或当前身份无权访问"

MIN_SCORE = 2.0  # one shared bigram is noise, not a match (same as metric matching)

# Cosine floor. Embeddings give every pair of texts *some* similarity, so
# without a floor an unrelated question always retrieves the top chunk and
# "no relevant evidence" becomes unreachable.
MIN_SIMILARITY = 0.35


@dataclass(frozen=True)
class RetrievalScope:
    """What one request is allowed to see.

    Derived from a trusted :class:`ActorContext` and nothing else, so a
    scope cannot be widened by anything the model or a document says.
    """

    subject_id: str
    workspace_id: str


def scope_of(actor: ActorContext) -> RetrievalScope:
    """The only way to build a scope."""
    return RetrievalScope(subject_id=actor.subject_id, workspace_id=actor.workspace_id)


class KnowledgeProvider(Protocol):
    """Contract for document evidence.

    Implementers must apply ``scope`` during candidate generation, not to the
    results. An implementation that cannot do that must not be offered on a
    multi-user path at all.
    """

    def search(self, scope: RetrievalScope, query: str, *, limit: int) -> tuple[EvidenceHit, ...]:
        """Authorised chunks relevant to ``query``, best first."""
        ...

    def read(self, scope: RetrievalScope, ref: EvidenceRef) -> Evidence:
        """Re-read one citation, re-checking authorisation. Never a cache."""
        ...

    def check_refs(
        self, scope: RetrievalScope, refs: tuple[EvidenceRef, ...]
    ) -> tuple[RefStatus, ...]:
        """Whether each citation still stands, in the order given."""
        ...


class LocalKnowledgeProvider:
    """Keyword retrieval over a local :class:`SqliteKnowledgeIndex`."""

    def __init__(
        self, index: SqliteKnowledgeIndex, embedder: EmbeddingClient | None = None
    ) -> None:
        self.index = index
        self._embedder = embedder

    @property
    def is_semantic(self) -> bool:
        """Whether this provider ranks semantically. Reported, never assumed.

        Degrading to keyword because no embeddings endpoint was configured is
        a legitimate mode, but a silent one would let a demo claim semantic
        retrieval it never performed (K10).
        """
        return self._embedder is not None

    def search(self, scope: RetrievalScope, query: str, *, limit: int) -> tuple[EvidenceHit, ...]:
        """Score every chunk *in this workspace* against the question.

        The baseline is the same tokeniser and the same noise floor as metric
        matching: a single shared bigram means two texts both contain 用户,
        not that one answers the other.
        """
        if self._embedder is not None:
            semantic = self._semantic(scope, query, limit)
            if semantic is not None:
                return semantic
        wanted = tokens(query)
        scored: list[tuple[float, EvidenceHit]] = []
        for chunk in self.index.chunks_in(scope.workspace_id):
            overlap = len(wanted & self.index.terms_of(scope.workspace_id, chunk.chunk_id))
            if overlap < MIN_SCORE:
                continue
            ref = EvidenceRef(
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                content_hash=chunk.content_hash,
            )
            scored.append((float(overlap), EvidenceHit(ref=ref, chunk=chunk, score=float(overlap))))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return tuple(hit for _, hit in scored[:limit])

    def _semantic(
        self, scope: RetrievalScope, query: str, limit: int
    ) -> tuple[EvidenceHit, ...] | None:
        """Rank by cosine similarity, or None when nothing is embedded yet.

        Falling back rather than returning empty: an un-embedded corpus is a
        setup step not yet run, and answering "no evidence" for it would be
        the same lie as answering it for a document that says nothing.
        """
        assert self._embedder is not None
        vectors = self.index.vectors_in(scope.workspace_id)
        if not vectors:
            return None
        query_vector = self._embedder.embed([query])[0]
        scored: list[tuple[float, EvidenceHit]] = []
        for chunk in self.index.chunks_in(scope.workspace_id):
            vector = vectors.get(chunk.chunk_id)
            if vector is None:
                continue
            score = cosine(query_vector, vector)
            if score < MIN_SIMILARITY:
                continue
            ref = EvidenceRef(
                doc_id=chunk.doc_id, chunk_id=chunk.chunk_id, content_hash=chunk.content_hash
            )
            scored.append((score, EvidenceHit(ref=ref, chunk=chunk, score=score)))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return tuple(hit for _, hit in scored[:limit])

    def read(self, scope: RetrievalScope, ref: EvidenceRef) -> Evidence:
        """Fetch the cited chunk, or refuse.

        Called again at confirm and execute time rather than reusing what
        search returned: the gap between reading a draft and running it is
        exactly where access is withdrawn.
        """
        chunk = self.index.get(scope.workspace_id, ref.chunk_id)
        if chunk is None:
            raise EvidenceUnavailable(_UNAVAILABLE)
        return Evidence(ref=ref, chunk=chunk)

    def check_refs(
        self, scope: RetrievalScope, refs: tuple[EvidenceRef, ...]
    ) -> tuple[RefStatus, ...]:
        """Re-check citations before confirming and before executing (§4.5.6)."""
        return tuple(self._status(scope, ref) for ref in refs)

    def _status(self, scope: RetrievalScope, ref: EvidenceRef) -> RefStatus:
        chunk = self.index.get(scope.workspace_id, ref.chunk_id)
        if chunk is None:
            return RefStatus.UNAVAILABLE
        if ref.content_hash and ref.content_hash != chunk.content_hash:
            return RefStatus.CHANGED
        return RefStatus.OK
