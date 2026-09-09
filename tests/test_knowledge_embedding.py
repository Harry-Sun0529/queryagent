"""Slice 1B: the optional semantic path. Zero network.

Uses httpx.MockTransport, the same way test_openai_backend.py does — the
point of a hand-written client over the vendor SDK is that its wire format
is ours to test.
"""

from __future__ import annotations

import json

import httpx
import pytest

from queryagent.knowledge.embedding import EmbeddingClient, cosine


def _client(vectors: list[list[float]], *, recorder: list | None = None) -> EmbeddingClient:
    def handle(request: httpx.Request) -> httpx.Response:
        if recorder is not None:
            recorder.append(json.loads(request.content))
        return httpx.Response(
            200, json={"data": [{"embedding": v, "index": i} for i, v in enumerate(vectors)]}
        )

    return EmbeddingClient(
        model="bge-m3",
        base_url="https://example.invalid/v1",
        api_key="k",
        client=httpx.Client(transport=httpx.MockTransport(handle)),
    )


def test_cosine_of_identical_vectors_is_one() -> None:
    assert cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_of_orthogonal_vectors_is_zero() -> None:
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_of_a_zero_vector_is_zero_not_a_crash() -> None:
    """An empty chunk can produce one; a division error here is not useful."""
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_embedding_returns_one_vector_per_input() -> None:
    client = _client([[1.0, 0.0], [0.0, 1.0]])
    assert client.embed(["a", "b"]) == ([1.0, 0.0], [0.0, 1.0])


def test_the_request_carries_the_configured_model() -> None:
    seen: list = []
    _client([[1.0]], recorder=seen).embed(["x"])
    assert seen[0]["model"] == "bge-m3"
    assert seen[0]["input"] == ["x"]


def test_an_api_key_is_required() -> None:
    """Keys come from the environment; an unset one must fail loudly."""
    with pytest.raises(ValueError, match="QUERYAGENT_EMBEDDING_API_KEY"):
        EmbeddingClient(model="m", base_url="https://x.invalid/v1", api_key="")


def test_a_short_response_is_an_error_not_a_silent_truncation() -> None:
    """Fewer vectors than inputs would misalign every chunk with its text."""
    client = _client([[1.0, 0.0]])
    with pytest.raises(ValueError, match="2"):
        client.embed(["a", "b"])
