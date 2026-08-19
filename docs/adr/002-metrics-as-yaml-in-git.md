# ADR-002: Metrics are a YAML file in git, not a vector store

Status: accepted · Date: 2026-08-19

## Decision

Business metric definitions live in one `metrics.yaml`, matched by alias
phrase hits + CJK-bigram keyword overlap (`YamlMetricStore`). No embeddings,
no vector database.

## Context

The target user is a small data team without governance infrastructure.
A YAML file is reviewable like code (a metric change is a PR diff), diffable,
blameable, and requires zero services. Embedding retrieval adds infra and
non-determinism for marginal recall at the scale of 5–50 metrics.

## Consequences

- (+) Zero infrastructure; metric changes carry authorship and history.
- (+) Matching is deterministic → clarify behaviour is testable.
- (−) Recall is bounded by aliases; unusual phrasings miss. `MetricStore`
  is a Protocol precisely so an embedding implementation can slot in later
  without touching the agent.
