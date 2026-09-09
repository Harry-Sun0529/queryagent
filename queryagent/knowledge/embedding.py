"""Optional semantic retrieval over an OpenAI-compatible embeddings endpoint.

Hand-written over httpx for the same reason the chat backend is (spec §四):
one implementation covers SiliconFlow, DashScope, OpenAI and a local vLLM,
and the dependency tree does not grow. Similarity is computed in plain
Python — a few hundred chunks of a few hundred floats does not need numpy,
and a vector database would contradict what this project is (ADR-007).

The key comes from ``QUERYAGENT_EMBEDDING_API_KEY``, separate from the chat
key on purpose: DeepSeek publishes no embeddings endpoint, so this is
usually a different provider entirely.

Deployment note that belongs in front of anyone enabling this: calling a
hosted endpoint means **company document text leaves the machine**. That is
a data-boundary decision for whoever deploys it, which is why semantic
retrieval is off unless configured.
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence

import httpx

ENV_KEY = "QUERYAGENT_EMBEDDING_API_KEY"

Vector = list[float]


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity, returning 0.0 for a zero vector rather than raising."""
    # strict=True: vectors of different lengths mean two models' outputs got
    # mixed, and a silently truncated similarity would rank on nonsense.
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    magnitude = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / magnitude if magnitude else 0.0


class EmbeddingClient:
    """Embeddings over the OpenAI-compatible protocol."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_s: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get(ENV_KEY, "")
        if not key:
            raise ValueError(
                f"{ENV_KEY} is not set. Semantic retrieval needs an embeddings "
                "endpoint; DeepSeek does not publish one, so this is usually a "
                "different provider than llm.base_url."
            )
        self._model = model
        self._url = base_url.rstrip("/") + "/embeddings"
        self._key = key
        self._client = client or httpx.Client(timeout=timeout_s)

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        """Embed a batch, in order.

        Raises:
            ValueError: The provider returned a different number of vectors
                than inputs — silently accepting that would pair every chunk
                after the gap with the wrong text.
        """
        response = self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._key}"},
            json={"model": self._model, "input": list(texts)},
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        vectors = [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
        if len(vectors) != len(texts):
            raise ValueError(
                f"embeddings endpoint returned {len(vectors)} vectors for {len(texts)} inputs"
            )
        return tuple(vectors)
