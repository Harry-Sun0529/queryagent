# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/). CLI arguments and config structure
enter the semver contract at v0.2.0; `metrics.yaml` required fields are
frozen from v0.1.1 (spec §四).

## [0.1.0] — 2026-08-17

First public release.

### Added

- **Agent core**: framework-free ReAct loop with four explicit termination
  conditions (final answer / turn limit / repeated-action dead-loop
  protection / safety violation), parse-failure retry with degraded direct
  answer, and a self-repair loop (database errors fed back verbatim, capped
  at 3 retries with `RetryEvent`s).
- **Clarify-instead-of-guess**: metrics carrying a `caution` field make the
  agent ask one clarifying question (`ClarifyEvent`) when the user's
  phrasing is ambiguous — with an explicit rule forbidding it from asking
  when the question already disambiguates.
- **Event-stream architecture**: `run_agent` yields `AgentEvent`s; the chat
  CLI and the eval runner are plain consumers of the same stream.
- **SQL safety whitelist**: token-level validation (sqlparse) allowing a
  single SELECT/CTE only; blocks DML/DDL, multi-statement payloads,
  comment smuggling, `INTO OUTFILE`, `FOR UPDATE`. Backed by
  connector-level timeouts/row caps and a documented read-only account.
- **Connectors**: MySQL (PyMySQL, pooled), SQLite (stdlib,
  progress-handler timeout), ClickHouse (optional extra) — all verified
  against live databases in the integration suite.
- **LLM backends**: Anthropic, plus a hand-written OpenAI-compatible
  backend (httpx) covering DeepSeek/Qwen/GLM/OpenAI/vLLM/Ollama via
  `base_url`.
- **Metrics**: YAML store with alias + CJK-bigram keyword matching, top-k
  prompt injection, answer citation of the metric used.
- **Evaluation**: 20-case self-built suite (incl. should-ask / must-not-ask
  clarify controls), five-metric runner comparing executed result sets
  (order-insensitive multiset + float tolerance), fixed-seed public
  benchmark subset tooling, `queryagent eval` with dual-model overrides.
- **Demo**: fictional e-commerce dataset (50k users / ~170k orders)
  generated from a dialect-agnostic IR into MySQL, SQLite and ClickHouse;
  docker-compose with read-only demo accounts.
