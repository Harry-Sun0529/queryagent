"""Data model for a confirmable business definition (handoff §9.1).

Everything here is immutable and hashable by *meaning*. The hash is what
binds "what the user confirmed" to "what gets executed": a version number
alone can be replayed, but a content hash cannot be made to agree with
semantics it does not describe.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RuleSource(Enum):
    """Where one rule of a 口径 came from.

    Kept explicit because the whole product problem is that people cannot
    tell a documented rule from someone's assumption. ``DOC`` therefore
    requires a citation; ``USER`` marks a convention agreed for this request
    only and must never be rendered as if the document said it (D07).
    ``HISTORY`` is a choice this subject confirmed on an earlier run, offered
    again (T42): theirs, but not made this time, and never a team standard.
    ``AGENT`` is a value an agent filled in over MCP on the subject's behalf
    (T44, ADR-013): neither what a document says nor what the person agreed,
    until the person reads it on the sheet and confirms.
    """

    DOC = "doc"
    USER = "user"
    MAINTAINER = "maintainer"
    HISTORY = "history"
    AGENT = "agent"


@dataclass(frozen=True)
class Rule:
    """One semantic field of a business definition, with its provenance."""

    key: str
    value: str
    source: RuleSource
    evidence_ref: str = ""
    note: str = ""
    implies: tuple[str, ...] = ()
    """Variant keys whose maintainer-declared wording the cited quote contains
    (T39). Empty when the rule cites nothing, or corresponds to no reading."""

    def __post_init__(self) -> None:
        """Structural checks only.

        This is a non-emptiness assertion, *not* a validity check: any string
        satisfies it. Whether a citation resolves to a chunk the actor was
        actually shown is established server-side by the evidence extraction
        pipeline, and whether a caller may claim DOC provenance at all is
        decided by ``QueryWorkflow.amend``. Do not read this constructor as
        the type system having guaranteed provenance.
        """
        if not self.key:
            raise ValueError("rule key must not be empty")
        if self.source is RuleSource.DOC and not self.evidence_ref:
            raise ValueError("a doc-sourced rule needs an evidence_ref to cite")
        if self.source is RuleSource.HISTORY and not self.note:
            raise ValueError("a history rule must say which earlier choice it repeats")

    @property
    def is_user_supplied(self) -> bool:
        """True for rules the user agreed this time, not documented facts."""
        return self.source is RuleSource.USER


# Maintainer-owned vocabulary. Extraction fills these holes; it never digs
# new ones — a model inventing a rule key would otherwise create a blocking
# `missing` entry out of nothing and no draft would ever be confirmable
# (§4.5.5).
ALLOWED_RULE_KEYS = (
    "counting_basis",
    "filters",
    "time_window",
    "dedup",
    "refund_handling",
    "amount_basis",
)

VARIANT_RULE_KEY = "variant"
"""Which maintainer-declared reading runs."""

PERIOD_RULE_KEY = "period"
"""The statistical period: an absolute range the user confirmed (slice 1C).

Only the user sets it — from the question's time words, or stated on
purpose. Document extraction cannot: its allowed keys exclude it, so a
handbook sentence cannot change which dates a query covers.
"""

GROUP_RULE_KEY = "group_by"
"""How the result is split (T38): by day, week or month, by a dimension a
maintainer declared, or explicitly not at all. Like the period, only the
user sets it; documents cannot, so a handbook cannot turn a number into a
table or a table into a number."""

FILTER_RULE_KEY = "filter"
"""One declared value of one dimension the result is restricted to (T43),
``dim:channel=ads``, or ``none``. Like the period and the grouping, only the
user sets it; documents cannot restrict what a number counts."""

PREVIOUS_CHOICE_KEY = "previous_choice"
"""A reading this subject confirmed before that differs from the one the
documents now select (T42). Shown and hashed; never compiled, never reused."""

COMPILED_RULE_KEYS = (VARIANT_RULE_KEY, PERIOD_RULE_KEY, GROUP_RULE_KEY, FILTER_RULE_KEY)
"""Rules the compiler turns into SQL. Every other rule explains the 口径."""

REQUIRABLE_RULE_KEYS = (*ALLOWED_RULE_KEYS, PERIOD_RULE_KEY)
"""Keys a metric may list in ``required_rules``: every extractable key, plus
the period, which only the user can fill."""

CONFLICT_SEPARATOR = ":"


@dataclass(frozen=True)
class Candidate:
    """One competing reading of the same metric (D02: conflicts stay visible)."""

    key: str
    label: str
    summary: str
    evidence_ref: str = ""
    implies: tuple[str, ...] = ()
    """For one side of a document disagreement: the readings its quote
    corresponds to, so adopting it can settle which one runs (T39)."""

    @property
    def rule_key(self) -> str:
        """The rule that choosing this candidate would fill.

        Two kinds of candidate share this type. A maintainer-declared variant
        (key ``registered``) decides what executes. One side of a document
        disagreement (key ``counting_basis:1``) decides what the 口径 means
        and executes nothing. Keeping them apart is what stops a user being
        asked to pick a handbook sentence as if it were a query.
        """
        if CONFLICT_SEPARATOR in self.key:
            return self.key.split(CONFLICT_SEPARATOR, 1)[0]
        return VARIANT_RULE_KEY


@dataclass(frozen=True)
class BusinessDefinition:
    """The structured 口径 a user is asked to confirm.

    ``missing`` names rules that are genuinely undetermined. They are part of
    the hash on purpose: "we do not know how refunds are handled" is a
    different statement than any particular answer to it, and confirming one
    must not silently satisfy the other.
    """

    metric: str
    display_name: str
    rules: tuple[Rule, ...] = ()
    missing: tuple[str, ...] = ()
    candidates: tuple[Candidate, ...] = ()

    @property
    def is_complete(self) -> bool:
        """True when nothing required is still undetermined."""
        return not self.missing

    def rule(self, key: str) -> Rule | None:
        """Look one rule up by key."""
        return next((r for r in self.rules if r.key == key), None)

    def candidate(self, key: str) -> Candidate | None:
        """Look one competing reading up by key."""
        return next((c for c in self.candidates if c.key == key), None)

    def with_rules(self, added: tuple[Rule, ...]) -> BusinessDefinition:
        """Return a copy with ``added`` replacing same-key rules.

        Supplying a rule also removes its key from ``missing``: answering the
        open question is what closes it.
        """
        replaced = {rule.key: rule for rule in added}
        kept = tuple(r for r in self.rules if r.key not in replaced)
        return BusinessDefinition(
            metric=self.metric,
            display_name=self.display_name,
            rules=kept + added,
            missing=tuple(k for k in self.missing if k not in replaced),
            candidates=self.candidates,
        )

    def content_hash(self) -> str:
        """Hash of meaning: rule keys/values/sources and what is still missing.

        Rules are sorted, so reordering the confirmation screen does not
        invalidate a confirmation. ``note`` is excluded — it is commentary.
        """
        payload = {
            "metric": self.metric,
            "rules": sorted(
                [
                    rule.key,
                    rule.value,
                    rule.source.value,
                    rule.evidence_ref,
                    *_implied(rule.implies),
                ]
                for rule in self.rules
            ),
            "missing": sorted(self.missing),
            # Candidate wording is on the screen the user approves, so it is
            # part of what they approved. Silently rewording an option they
            # chose between must invalidate the confirmation.
            "candidates": sorted(
                [c.key, c.label, c.summary, c.evidence_ref, *_implied(c.implies)]
                for c in self.candidates
            ),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _implied(implies: tuple[str, ...]) -> list[str]:
    """Which reading a quote corresponds to is on the sheet, so it is hashed.

    Only when present: a draft with no correspondences hashes exactly as it
    did before T39, so confirmations recorded by v0.7 still match.
    """
    return ["implies=" + ",".join(implies)] if implies else []


class Channel(Enum):
    """Which door a request came through (T44/T45, ADR-013).

    Two of them have a person on the other side: the terminal and the local
    confirmation page. The third has an agent. Only the first two may
    confirm, and a confirmation records which one it came through.
    """

    CLI = "cli"
    WEB = "web"
    MCP = "mcp"

    @property
    def is_human(self) -> bool:
        """True where a person reads the sheet: the only doors that may confirm."""
        return self is not Channel.MCP


HUMAN_CHANNELS = tuple(channel for channel in Channel if channel.is_human)


@dataclass(frozen=True)
class ActorContext:
    """A trusted caller identity (D11).

    Constructed only by a trusted entry point — the local CLI user, a Web
    session, an MCP host that authenticated the caller. Never parsed out of
    model output or tool arguments: a ``subject_id`` a model proposed is a
    string, not an authorisation.

    ``channel`` is set by that entry point too. It is what makes a rule an
    agent wrote read 「Agent 代填」 rather than 「本次约定」, and what keeps an
    agent from confirming (ADR-013).
    """

    subject_id: str
    workspace_id: str
    roles: frozenset[str] = field(default_factory=frozenset)
    channel: Channel = Channel.CLI

    def __post_init__(self) -> None:
        if not self.subject_id:
            raise ValueError("subject_id must not be empty")
        if not self.workspace_id:
            raise ValueError("workspace_id must not be empty")

    @property
    def authoring_source(self) -> RuleSource:
        """The provenance of a rule this caller supplies: theirs, or their agent's."""
        return RuleSource.USER if self.channel.is_human else RuleSource.AGENT


class DraftStatus(Enum):
    """Draft lifecycle (handoff §9.2)."""

    NEEDS_INPUT = "needs_input"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


class RunStatus(Enum):
    """Execution lifecycle."""

    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class DefinitionDraft:
    """A versioned, persisted draft belonging to exactly one subject."""

    draft_id: str
    request_id: str
    subject_id: str
    workspace_id: str
    question: str
    version: int
    status: DraftStatus
    definition: BusinessDefinition
    created_at: datetime
    updated_at: datetime

    @property
    def definition_hash(self) -> str:
        return self.definition.content_hash()


@dataclass(frozen=True)
class Confirmation:
    """Proof that a subject approved one exact draft version.

    Binds all three of draft, version and content hash. Executing needs all
    three to still agree with what the store holds (§9.2 invariants 4-5).
    """

    confirmation_id: str
    draft_id: str
    draft_version: int
    definition_hash: str
    subject_id: str
    confirmed_at: datetime
    channel: Channel = Channel.CLI
    """Where the person confirmed (H9). Never MCP. Confirmations recorded
    before 1.0 came from the terminal, the only door there was."""


class DraftProgress(Enum):
    """Where one draft stands, as an agent or a page asks after it (T44).

    Derived, not stored: the draft's status, whether a person confirmed its
    current version, and whether that confirmation has run.
    """

    NEEDS_INPUT = "needs_input"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    EXECUTED = "executed"


@dataclass(frozen=True)
class QueryRun:
    """One execution attempt against a confirmation."""

    run_id: str
    draft_id: str
    confirmation_id: str
    subject_id: str
    idempotency_key: str
    status: RunStatus
    sql: str = ""
    params: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[object, ...], ...] = ()
    truncated: bool = False
    error: str = ""
    freshness_sql: str = ""
    """The statement that dated the data; '' when the mapping had no time column."""
    data_through: str = ""
    """ISO date of the newest record it found; '' when unknown."""
    expected_through: str = ""
    """ISO date the maintainer's declared cadence said the data should reach
    when this ran (T41); '' when no cadence was declared."""
    mapping_fingerprint: str = ""
    """Digest of the mapping that ran (T42), so a remembered choice can tell
    whether what it chose has changed since; '' for runs before 0.9."""
