# ADR-012: A remembered choice is a proposal on the sheet, not a standard

Status: accepted · Date: 2026-09-11

## Decision

When a subject asks about a metric again, the draft may offer the choices
they confirmed on their last successful run of it, in the same workspace, as
rules of a new source, `RuleSource.HISTORY`, shown as 「历史选择」 with the
day they were confirmed. What is offered:

- the executable reading (`variant`), if it is still one of today's options;
- a document's wording they adopted, if the same wording from the same place
  is still an option, and the document still checks out for them;
- their own words for a gap nothing states, if documents have not since
  begun to disagree about it.

Never the period or the split (they describe one question), never another
subject's choices, and never anything the documents or the maintainer
already state: history fills gaps and overrides nothing. When the documents
now select a different reading, it stays, and the sheet shows the
remembered one beside it as 「上次的选择」.

Nothing is offered when the mapping that ran has changed since (a
fingerprint recorded on each run), when the choice is older than
`workflow.history_max_age_days`, when the draft was amended after it was
confirmed, or when nobody will read the sheet (`--yes`; `--no-history` turns
it off explicitly).

History is derived from confirmations and successful runs already in the
store, not kept in a table of its own.

## Context

The handoff: "可复用历史选择但不是团队标准". The failure modes are an
invisible team standard (one person's choice reaching another), a stale
reading returning after its SQL changed, and a script silently running a
reading nobody looked at this time.

## Consequences

- (+) A repeat question needs no repeat choice, and the sheet still says
  whose choice it was and when.
- (+) History is in the content hash: a remembered rule and the same rule
  typed again are different confirmations, because they were different acts.
- (+) A lapsed choice is not offered, and the lapse is not explained, so a
  withdrawn document is not named through someone's history.
- (−) `RuleSource.HISTORY` is a one-way change: v0.8 cannot open a draft
  that contains it. Drafts written by v0.8 still open in v0.9.
- (−) Runs recorded before 0.9 have no fingerprint and are never offered.
- (−) A remembered choice can make confirming cheaper than reading. The
  mark, the date and the conflict line are the mitigation; confirmation
  itself is unchanged.
