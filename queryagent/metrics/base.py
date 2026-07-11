"""Metric model and store abstraction (spec §二).

``MetricStore`` is the reserved seam for future matching implementations
(e.g. embedding-based, v0.4+ backlog) — the protocol deliberately does not
promise any particular matching algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Metric:
    """One declared business metric.

    Required fields (frozen at v0.1.1, spec §三): ``name``, ``definition``.
    Optional fields may grow over time but never change meaning.

    Attributes:
        name: Unique identifier, e.g. "new_users".
        definition: Natural-language business definition; the main text
            injected into the prompt.
        display_name: Human-facing name, e.g. "新增用户".
        aliases: Alternative names used for matching.
        caution: Optional warning about competing definitions; the v0.2.0
            clarify feature triggers on this field.
        tables: Tables this metric touches (aids schema trimming later).
        sql_hint: Optional SQL fragment hint for the model.
    """

    name: str
    definition: str
    display_name: str = ""
    aliases: tuple[str, ...] = ()
    caution: str = ""
    tables: tuple[str, ...] = ()
    sql_hint: str = ""


class MetricStore(Protocol):
    """Contract for metric lookup and question matching."""

    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        """Return up to ``top_k`` metrics relevant to the question, best first."""
        ...

    def get(self, name: str) -> Metric | None:
        """Exact lookup by unique metric name."""
        ...
