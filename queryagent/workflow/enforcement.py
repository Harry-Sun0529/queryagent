"""Whether a document's rule is one the executed query applies (T39).

Until now the result could only say "the system does not check whether the
two agree" — beside a sheet that might read 「文档依据：按注册日期计数」 over
a query counting by first order. Documents still cannot become SQL (that
boundary does not move); what changes is that they can be *matched* to a
reading a maintainer made executable.

The match is deterministic by construction. Each structured mapping declares
the rule keys its statement applies and the words a document describing that
would use (``enforces:`` in the mappings file). A quote that already passed
verbatim validation *corresponds* to a reading when it contains one of that
reading's words. No model judges meaning here, so the claim is exactly as
strong as the maintainer's word list — and both the words and the quote are
on the sheet for a person to judge.

A quote naming two readings in their own words (「不按注册日期，按首单日期」)
contains both, and substring matching cannot tell which it means. Then no
correspondence is claimed at all.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from queryagent.text import normalize
from queryagent.workflow.mappings import QueryMapping
from queryagent.workflow.models import VARIANT_RULE_KEY, BusinessDefinition, Rule, RuleSource

Terms = Mapping[str, Mapping[str, tuple[str, ...]]]
"""variant key → rule key → the words a document would use for it."""

ENFORCED = "enforced"
CONFLICTS = "conflicts"
UNCHECKED = "unchecked"


def enforcement_table(
    mappings: Mapping[tuple[str, str], str | QueryMapping],
) -> dict[str, dict[str, dict[str, tuple[str, ...]]]]:
    """metric → variant → rule key → words, from the structured mappings."""
    table: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {}
    for (metric, variant), entry in mappings.items():
        if isinstance(entry, QueryMapping) and entry.enforces:
            table.setdefault(metric, {})[variant] = dict(entry.enforces)
    return table


def _fold(text: str) -> str:
    return normalize(text).lower()


def implied_variants(terms: Terms, key: str, quote: str) -> tuple[str, ...]:
    """The readings whose declared words for ``key`` appear in ``quote``.

    A word only one matched reading declares singles that reading out; words
    every matched reading shares (both 新增用户 readings exclude test
    accounts) mean each of them applies the rule. So: one reading with words
    of its own → that reading; two or more → the quote names several, and
    nothing is claimed; none → all the readings that matched.
    """
    folded = _fold(quote)
    matched: dict[str, frozenset[str]] = {}
    for variant, by_key in terms.items():
        hits = frozenset(word for word in by_key.get(key, ()) if _fold(word) in folded)
        if hits:
            matched[variant] = hits
    own = [
        variant
        for variant, hits in matched.items()
        if hits - frozenset().union(*(h for v, h in matched.items() if v != variant))
    ]
    if len(own) > 1:
        return ()
    if own:
        return (own[0],)
    return tuple(sorted(matched))


def verdict(implies: tuple[str, ...], chosen: str) -> str:
    """ENFORCED, CONFLICTS or UNCHECKED for one rule against the chosen reading."""
    if not implies or not chosen:
        return UNCHECKED
    return ENFORCED if chosen in implies else CONFLICTS


def consistent_variant(rules: Iterable[Rule], variants: set[str]) -> tuple[str, Rule] | None:
    """The one reading every corresponding rule allows, and a rule that chose it.

    None unless the rules narrow the choice to exactly one reading: rules
    every reading applies (a shared filter) do not choose anything, and rules
    pointing different ways leave nothing consistent.
    """
    grounded = [r for r in rules if r.implies and r.key != VARIANT_RULE_KEY]
    consistent = set(variants)
    for rule in grounded:
        consistent &= set(rule.implies)
    anchor = next((r for r in grounded if not variants <= set(r.implies)), None)
    if len(consistent) != 1 or anchor is None:
        return None
    return next(iter(consistent)), anchor


def preselect_variant(definition: BusinessDefinition) -> BusinessDefinition:
    """Fill the reading the documents agree on, as 「文档依据」 with its citation.

    This is the one way a document rule reaches the SQL: by choosing among
    statements a maintainer wrote. It is still only a draft — the sheet shows
    the reading and its source, the user confirms or overrides it. Nothing is
    chosen while a document disagreement is open, because adopting its other
    side would contradict the choice.
    """
    if VARIANT_RULE_KEY not in definition.missing:
        return definition
    pending = any(
        c.implies
        for c in definition.candidates
        if c.rule_key != VARIANT_RULE_KEY and c.rule_key in definition.missing
    )
    if pending:
        return definition
    variants = {c.key for c in definition.candidates if c.rule_key == VARIANT_RULE_KEY}
    documented = (r for r in definition.rules if r.source is RuleSource.DOC)
    found = consistent_variant(documented, variants)
    if found is None:
        return definition
    choice, anchor = found
    rule = Rule(
        VARIANT_RULE_KEY,
        choice,
        RuleSource.DOC,
        evidence_ref=anchor.evidence_ref,
        note="由文档依据对应",
    )
    return definition.with_rules((rule,))
