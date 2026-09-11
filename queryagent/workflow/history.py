"""A choice this subject confirmed before, offered again (slice 1D, T42, ADR-012).

The handoff asked for past choices to be reusable "but not as a team
standard". Three properties keep them that:

1. A remembered choice belongs to one person in one workspace. Nothing
   another subject confirmed is read, so history cannot become a shared
   口径 nobody agreed to.
2. It fills gaps and overrides nothing. A reading the documents select, or a
   period or split the question states, stays as it is. A remembered reading
   that disagrees with the documents is shown beside them, not over them.
3. It is marked 「历史选择」 with the day it was confirmed, it is part of the
   content hash, and the user still confirms the whole sheet. The sheet
   proposes it; nobody decides it for anyone.

A remembered choice lapses when what it was about has moved: the mapping
that ran has changed, the option it picked is no longer offered, a document
it adopted no longer checks out for this subject, or it is older than the
maintainer's limit. A lapsed choice is simply not offered. Which document
lapsed is not said, because saying so can disclose one (the 1B wording).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone, tzinfo

from queryagent.knowledge.models import EvidenceRef, RefStatus
from queryagent.knowledge.provider import scope_of
from queryagent.workflow.models import (
    FILTER_RULE_KEY,
    GROUP_RULE_KEY,
    PERIOD_RULE_KEY,
    PREVIOUS_CHOICE_KEY,
    VARIANT_RULE_KEY,
    ActorContext,
    BusinessDefinition,
    Rule,
    RuleSource,
)
from queryagent.workflow.service import DraftBuilder, RefChecker
from queryagent.workflow.store import SqliteWorkflowStore

NOT_REMEMBERED = (PERIOD_RULE_KEY, GROUP_RULE_KEY, FILTER_RULE_KEY, PREVIOUS_CHOICE_KEY)
"""Rules about one question rather than about the metric: never carried over."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HistoryDraftBuilder:
    """Wraps another builder and offers the subject's last confirmed choices for what is open."""

    def __init__(
        self,
        inner: DraftBuilder,
        store: SqliteWorkflowStore,
        *,
        fingerprint: Callable[[BusinessDefinition], str],
        ref_checker: RefChecker | None,
        zone: tzinfo,
        max_age_days: int,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """
        Args:
            inner: The builder whose draft this one completes.
            store: Where confirmations and runs are recorded.
            fingerprint: The digest of the mapping a definition would run today
                (``TemplateCompiler.fingerprint``), compared with the one
                recorded when the remembered choice ran.
            ref_checker: Re-checks the documents a remembered choice adopted;
                without one, such a choice cannot be verified and is dropped.
            zone: The business time zone the confirmation date is shown in.
            max_age_days: ``workflow.history_max_age_days``.
            clock: Now, in UTC.
        """
        self._inner = inner
        self._store = store
        self._fingerprint = fingerprint
        self._ref_checker = ref_checker
        self._zone = zone
        self._max_age = timedelta(days=max_age_days)
        self._clock = clock

    def build(self, question: str, actor: ActorContext | None = None) -> BusinessDefinition:
        current = self._inner.build(question, actor)
        if actor is None:
            return current
        found = self._store.last_confirmed(
            actor.subject_id, actor.workspace_id, current.metric, self._clock() - self._max_age
        )
        if found is None:
            return current
        ran_fingerprint = found.mapping_fingerprint
        if not ran_fingerprint or ran_fingerprint != self._fingerprint(found.definition):
            # The mapping behind that choice changed — or the run predates
            # fingerprints, and nobody can tell whether it did.
            return current
        day = f"{found.confirmed_at.astimezone(self._zone):%Y-%m-%d}"
        remembered = [
            rule
            for rule in found.definition.rules
            if rule.source in (RuleSource.USER, RuleSource.HISTORY)
            and rule.key not in NOT_REMEMBERED
            and self._still_stands(actor, rule)
        ]
        return _offer(current, remembered, day)

    def _still_stands(self, actor: ActorContext, rule: Rule) -> bool:
        """A choice resting on a document is offered only while that document checks out.

        That includes a reading chosen *because* of an adopted wording (「由采用
        的文档写法对应」): it rests on the document as much as the wording does.
        Found in review — the wording lapsed while the reading it chose stayed.
        """
        if not rule.evidence_ref:
            return True
        if self._ref_checker is None:
            return False
        try:
            ref = EvidenceRef.parse(rule.evidence_ref)
        except ValueError:
            return False
        statuses = self._ref_checker.check_refs(scope_of(actor), (ref,))
        return all(status is RefStatus.OK for status in statuses)


def _offer(current: BusinessDefinition, remembered: list[Rule], day: str) -> BusinessDefinition:
    """Fill what ``current`` still lacks from ``remembered``; override nothing."""
    note = f"沿用你 {day} 确认过的选择"
    offered: list[Rule] = []
    shown: list[Rule] = []
    for rule in remembered:
        if rule.key == VARIANT_RULE_KEY:
            chosen = current.rule(VARIANT_RULE_KEY)
            if chosen is not None:
                if chosen.source is not RuleSource.DOC or chosen.value == rule.value:
                    continue
                # E12: the documents chose another reading. Theirs stays; the
                # sheet says what this person picked last time.
                candidate = current.candidate(rule.value)
                label = candidate.label if candidate else rule.value
                shown.append(
                    Rule(
                        PREVIOUS_CHOICE_KEY,
                        f"{label}（你 {day} 确认过；与本次的文档依据不同，未沿用）",
                        RuleSource.HISTORY,
                        note=note,
                    )
                )
            elif rule.key in current.missing and current.candidate(rule.value) is not None:
                offered.append(Rule(VARIANT_RULE_KEY, rule.value, RuleSource.HISTORY, note=note))
            continue
        if rule.key not in current.missing:
            continue
        options = [c for c in current.candidates if c.rule_key == rule.key]
        if rule.evidence_ref:
            # A document's wording the user adopted: offered only if the same
            # wording, from the same place, is one of today's options.
            wanted = (rule.value, rule.evidence_ref)
            same = next((c for c in options if (c.summary, c.evidence_ref) == wanted), None)
            if same is not None:
                offered.append(
                    Rule(
                        rule.key,
                        rule.value,
                        RuleSource.HISTORY,
                        evidence_ref=rule.evidence_ref,
                        note=note,
                        implies=same.implies,
                    )
                )
        elif not options:
            # The user's own words for a gap nothing states — unless documents
            # now disagree about it, which is a new question to put to them.
            offered.append(Rule(rule.key, rule.value, RuleSource.HISTORY, note=note))
    added = tuple(_consistent(offered)) + tuple(shown)
    return current.with_rules(added) if added else current


def _consistent(offered: list[Rule]) -> list[Rule]:
    """Drop a remembered reading that a remembered document wording now points away from."""
    variant = next((r for r in offered if r.key == VARIANT_RULE_KEY), None)
    if variant is None:
        return offered
    if any(r.implies and variant.value not in r.implies for r in offered if r is not variant):
        return [r for r in offered if r is not variant]
    return offered
