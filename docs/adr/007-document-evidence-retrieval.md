# ADR-007: Document evidence retrieval, and what it does not change

Status: accepted · Date: 2026-09-09

## Decision

Business rules can be drafted from company documents, retrieved under the
asking identity's workspace and cited by file, section and line. Retrieval
ships with a keyword baseline that needs no new dependency. A semantic
implementation sits behind the same `KnowledgeProvider` seam, is optional,
is off unless configured, and calls an OpenAI-compatible `/v1/embeddings`
endpoint rather than embedding a vector database.

The index is a local SQLite file. No service, no vector store, no daemon.

## Context

[ADR-002](002-metrics-as-yaml-in-git.md) decided that *metric matching* is a
YAML file plus alias and bigram overlap — "No embeddings, no vector
database" — because at 5–50 metrics embedding retrieval buys marginal recall
for real infrastructure. **That decision stands and this ADR does not touch
it.** `metrics.yaml` is still matched exactly as before.

This is a different problem. The product exists because the same business
phrase means different numbers to different teams, and the reason is that
their handbooks disagree. A maintainer file cannot show that disagreement:
it *is* the single authoritative definition the product exists to doubt.
Only the documents can put two readings side by side with a source attached.

Document corpora are also not 5–50 short strings. Phrasing varies, and the
question "新增用户" has to reach a section headed 「拉新口径」.

## Consequences

- (+) 「文档依据」 becomes producible. Until now the workflow layer could
  declare the provenance mark but never emit it.
- (+) Base install unchanged: keyword retrieval needs no new dependency, and
  the index is one file. DOCX is parsed with `zipfile` + `ElementTree`; only
  PDF adds an extra.
- (−) The README's "no vector store / Infrastructure: none" claims now need
  qualifying rather than restating. Core install: still true. With semantic
  retrieval configured: an external embedding endpoint is called, and
  **document text leaves the machine**. That is a data-boundary decision for
  whoever deploys it, so it is off by default and must be stated, not
  buried.
- (−) A second retrieval implementation is a second place workspace scoping
  can break. The `KnowledgeProvider` Protocol takes a scope on every method
  with no overload without one, so "fetch then filter" cannot be written;
  the provider conformance tests are the admission gate for any new
  implementation.
- (−) Retrieval quality is now a thing that can regress silently. Keyword
  and semantic are reported separately and never merged into one "RAG
  accuracy" number.
