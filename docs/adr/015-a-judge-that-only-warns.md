# ADR-015: A second model may doubt a restatement; it may only warn

Status: accepted · Date: 2026-11-16

## Decision

With `knowledge.faithfulness_check: true`, preparing a draft makes one more
model call. It is shown each document rule's quote — read back from the
document, not the extractor's copy — beside the extractor's restatement, and
asked whether the restatement says what the quote says.

- A rule it calls unfaithful stays on the sheet, with a line under it:
  「⚠ 这句转述可能与引文不一致（评审理由：…）。请对照出处原文。」
- The warning is hashed with the rule, stored with the draft, follows one
  side of a disagreement through adoption, and is named again on the result.
- It drops nothing, blocks no confirmation and changes nothing that runs.
- "Unsure", and output that cannot be read, warn about nothing. They are
  never read as "faithful".
- If the call itself fails, preparing the draft fails. A sheet prepared with
  the check on must not be one the check never ran on.
- Off by default. Without the key, drafts, hashes and the number of model
  calls are what they were in 1.0.

## Context

Extraction is checked for what can be checked exactly: the citation is one
the model was shown, the quote is verbatim, the rule's numbers are in the
quote. Meaning is not checked. 「不含测试账号」 restated as 「含测试账号」
passes all three and arrives under a real source. SECURITY.md has said so
since 0.6 ("Not guaranteed").

A judge is a model too. Letting it gate anything would be one unmeasured
model vouching for another, so two things were fixed before it was built:
it is measured first, and whatever the measurement says, it only warns.

## What was measured (2026-11-16, `deepseek-chat`, temperature 0)

`eval/knowledge/faithfulness.yaml`, 90 pairs, three runs
(`eval/run_faithfulness_check.py`):

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| unfaithful pairs called unfaithful | 52/52 | 52/52 | 52/52 |
| faithful pairs called unfaithful | 0/38 | 0/38 | 0/38 |
| of which the hard tier | 10/10, 0/8 | 10/10, 0/8 | 10/10, 0/8 |
| adversarial pairs held | 5/5 | 5/5 | 5/5 |

The rule written beforehand asked for recall ≥ 85% and false alarms ≤ 10% in
every run, and every adversarial pair held. It is met.

**What these numbers are not.** Read this before quoting them.

- The pairs and their labels were written by an AI assistant. When the
  judge was measured and wired in, no person had read them. The project
  owner read all 90 on 2026-11-17 and kept every label (`reviewed_by` in the
  file; three judgement calls are named in its header). That settles whether
  the labels are right. It does not make the set independent: the pairs
  were still composed by a model of the kind being judged.
- A perfect score is a ceiling, not a measurement of how good the judge is.
  The first 72 pairs scored 72/72; a harder tier of 18 was added because a
  set nothing fails on measures nothing — and nothing failed on that either.
  The set does not yet contain a pair this judge gets wrong.
- The judge and the extractor are the same model. A blind spot they share is
  invisible here. No key for a second model family was available.
- On the example handbooks the real extractor restates almost verbatim: of 15
  real pairs the judge doubted none. The case this guards against — a
  careless or steered restatement — had to be constructed to be seen.

## Consequences

- (+) The one class of extraction error nothing detected now has a detector,
  and its reader is still the person with the quote in front of them.
- (+) Nothing about confirmation or execution moved. Turning it off is one
  key.
- (−) One more model call per prepared draft (about a second here).
- (−) A warning people learn to ignore is worse than none. The false-alarm
  bound in the acceptance rule exists for that reason; it was measured on 38
  faithful pairs, none of which the judge flagged.
- No warning does not mean the restatement was verified. SECURITY.md keeps
  saying so.
