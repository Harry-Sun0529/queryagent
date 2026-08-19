# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/). CLI arguments and config structure
enter the semver contract at v0.2.0; `metrics.yaml` required fields are
frozen from v0.1.1 (spec §四).

## [0.4.0] — 2026-08-19

### Added

- **Eval checkpointing**: each finished case is appended to
  `<output>.partial.jsonl` as it completes, and `--resume` reuses it — an
  expanded suite is ~45 minutes of paid API calls, and a blip at minute 40
  used to discard all of it.
- **Exit-code taxonomy** (ADR-006): 2 for user error, 70 (`EX_SOFTWARE`) for
  defects in QueryAgent, 75 (`EX_TEMPFAIL`) for retryable upstream trouble.
  Batch scripts can now tell "retry later" from "your config is wrong".
- Black-box tests for multi-turn session memory, verified non-vacuous by a
  mutation check.

### Changed

- **Benchmark samples expanded** (ADR-004 rewritten): the sealed test set
  goes from 30 to **200 freshly sampled** questions, dev from 30 to **100**
  (the 60 previously observed questions retired into dev); 198 held in
  reserve. Reason: at n=30 even a paired before/after comparison was
  underpowered — it needs 57–114 cases, while the earlier analysis had
  mistakenly applied an independent-samples formula and overstated the
  requirement.
- **The anchor rule is restated** as "never change the system in response to
  test results", replacing "run test only once" — the old wording described
  the mechanism, not the purpose it serves.
- Duplicate questions in upstream BIRD mini-dev are now collapsed (case ids
  key the resume log and the report table, so a duplicate silently skipped
  the second copy). Pool 500 → 498.

### Numbers

Measured on the **new** samples; earlier releases' numbers below were
measured on the now-retired 30-case samples and **are not comparable**.
Those entries keep their original values deliberately — a changelog records
what was published, not what we would prefer to have published.

A controlled decomposition ([eval/results/version-decomposition.md](eval/results/version-decomposition.md))
established that the drop from v0.2.0's 83% first-execution rate to
v0.3.0's 61–72% is **not a code regression**: with cases and configuration
held constant the v0.3.0 code scores +5pp higher, and the entire drop comes
from enabling the model's thinking mode, which lowers first-attempt accuracy
without lowering final accuracy.

## [0.3.0] — 2026-08-19

### Added

- **Observability**: event streams recorded to `.queryagent/traces/*.jsonl`
  and replayable with `queryagent replay`; on by default with a first-write
  privacy notice, `--no-trace` / `trace: false`, and `.queryagent/`
  gitignored (ADR-005).
- **Cost & latency accounting**: `UsageEvent` carries per-call tokens
  (including prompt-cache hits) and latency; eval reports gain tokens,
  cache-hit rate, latency and an upper-bound cost per case.
- **DeepSeek thinking-mode support**: `reasoning_content` is parsed and
  echoed back, without which turn 2 of any tool-using conversation failed
  with HTTP 400.
- **Actionable CLI errors**: six common failures (missing key, bad key,
  missing config, missing database, missing optional driver, invalid config)
  print one line of problem and one line of fix; `--verbose` keeps the
  traceback.
- **dev/test split for the public benchmark** (ADR-004 rewritten):
  `sample_cases(exclude=)` plus a committed seed-7 dev subset, disjoint from
  the sealed seed-42 test set by a tested property.
- Failing eval cases now report the agent's SQL next to the reference SQL.

### Changed

- System prompt instructs precise projection (select what was asked; context
  belongs in the answer text) — dev-set failure analysis showed half of all
  failures were shape, not substance. dev 33% → 47% after self-repair.

## [0.2.0] — 2026-08-19

### Added

- **Multi-turn chat**: follow-up questions see the session's earlier turns
  (`run_agent(..., conversation=)`); the context budget trims old
  conversation before the current run's tool exchanges, always in pairs.
- **`queryagent ask`** — one-shot, scriptable question (exit 0 on
  answer/clarify, 2 on a terminal error).
- **Transient-failure retry** in the OpenAI-compatible backend: transport
  errors, HTTP 429 and 5xx retried twice with linear backoff; plain 4xx
  fails immediately.
- Decision records `docs/adr/001–004`, repo-level `CONTEXT.md` (domain
  language + seam map), `docs/specs/` for in-flight work.

### Changed

- Example configs now default to DeepSeek via the OpenAI-compatible backend
  (the Anthropic block stays as a commented alternative); README quickstart
  leads with `OPENAI_API_KEY`.

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
