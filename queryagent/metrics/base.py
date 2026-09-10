"""Metric model and store abstraction (spec §二).

``MetricStore`` is the reserved seam for future matching implementations
(e.g. embedding-based, v0.4+ backlog) — the protocol deliberately does not
promise any particular matching algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MetricVariant:
    """One maintainer-declared competing reading of a metric (v0.6, D02/D09).

    ``caution`` is prose meant for a model to read; a variant is the same
    disagreement made selectable, so a user picks a reading and the choice
    can be bound into a confirmation. Maintainers declare these — the model
    does not get to invent a 口径 the business never agreed on.
    """

    key: str
    label: str
    definition: str


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
        variants: Competing readings a user may choose between.
        required_rules: Rule keys the 口径 must state before it can be
            confirmed. A gap the documents do not fill is listed as missing
            and has to be supplied by the user (§4.5.5, D07).
    """

    name: str
    definition: str
    display_name: str = ""
    aliases: tuple[str, ...] = ()
    caution: str = ""
    tables: tuple[str, ...] = ()
    sql_hint: str = ""
    variants: tuple[MetricVariant, ...] = ()
    required_rules: tuple[str, ...] = ()


class MetricStore(Protocol):
    """Contract for metric lookup and question matching."""

    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        """Return up to ``top_k`` metrics relevant to the question, best first."""
        ...

    def get(self, name: str) -> Metric | None:
        """Exact lookup by unique metric name."""
        ...
