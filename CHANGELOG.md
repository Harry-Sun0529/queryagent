# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/). CLI arguments and config structure
enter the semver contract at v0.2.0; `metrics.yaml` required fields are
frozen from v0.1.1 (spec §四).

## [Unreleased]

## [1.0.0] — 2026-09-11

The first release whose version number is a promise (ADR-014).
契约摘要：26f385531e97

### Added

- **Agents over MCP** (`queryagent mcp`, ADR-013). A stdio MCP server,
  written by hand, serving five tools: `list_metrics`, `prepare_query`,
  `amend_query`, `query_status` and `execute_query`. None of them confirms.
  - Identity is the `--subject` / `--workspace` the host's configuration
    starts the server with. A tool argument naming one is refused.
  - What the agent fills in is marked 「Agent 代填」 (`RuleSource.AGENT`),
    is hashed, is highlighted for the person, and is named on the result.
  - `execute_query` runs a draft only on a person's confirmation of its
    current version. One confirmation authorises one run, and asking again
    returns that run.
- **A person's doors.**
  - `queryagent web` is a local confirmation page, bound to 127.0.0.1 only.
    - Login is a one-time link printed on the terminal; the session is an
      `HttpOnly; SameSite=Strict` cookie.
    - Every request is checked in order: Host (DNS rebinding), session, then
      for a POST the Origin and an HMAC form token bound to the draft version
      and hash on screen (CSRF).
    - Everything is escaped, and the Content-Security-Policy runs no script
      (XSS).
  - `queryagent drafts` lists what waits on you.
  - `queryagent confirm <草案号>` confirms in the terminal and asks for
    anything still open first.
  - A confirmation records which door it came through (`cli` / `web`).
- **Workflow scenarios** (`eval/workflow/scenarios.yaml`,
  `eval/run_workflow_scenarios.py`, ADR-014 H10). 22 scenarios measure what
  the product guarantees: whether it asks what it must, and whether numbers
  agree with a Python recount over raw rows. Three hard gates must read zero:
  unconfirmed executions, cross-workspace canary leaks, and injection effects
  on what runs.
  - The scripted run: 22/22, all gates 0.
  - Three DeepSeek runs of the six document scenarios: 6/6 each, all gates 0.
  - The scripted subset runs in CI on a freshly generated demo database.
- **The library surface.** `from queryagent import QueryWorkflow,
  ActorContext, build_workflow, …`: the confirmed flow's types, errors and
  assembly are now in `__all__`.
- **Frozen surfaces, snapshotted** (`tests/contract/`): the CLI, exit codes,
  config keys, file keys, `__all__`, and the MCP input schemas. A change
  fails CI until the snapshot is regenerated *and* this file carries the new
  digest.
- **State files from 0.6–0.9**, written by those releases' own code, are
  kept as fixtures, and 1.0 reads and upgrades each of them.
- A release workflow: build, `twine check`, and a wheel smoke test in a
  clean virtualenv. Publishing goes through PyPI trusted publishing (OIDC)
  behind a `pypi` environment the maintainer approves, and TestPyPI is
  available as a rehearsal. CI now smoke-tests the wheel on every push.

### Changed

- `metrics.yaml` and `query_mappings.yaml` **refuse unknown keys**, naming
  the allowed ones. A misspelt `time_colum` used to be read as absent and
  silently dropped the period. Files that used only documented keys are
  unaffected.
- The workflow assembly moved out of the CLI into `workflow/wiring.py`
  (`build_workflow`), and the reading of typed answers into
  `workflow/answers.py`. The terminal, the page and the MCP server share
  one of each.
- A draft's citations are recorded by the service when it is prepared, not
  by each door.
- The confirmation sheet names who adopted a document wording (「本次约定」 or
  「Agent 代填」) instead of always saying 「本次约定」.
- `ActorContext` gains `channel` (default `cli`); `Confirmation` gains
  `channel`.

### Compatibility

- The state file's `confirmations` table gains a `channel` column, added
  automatically; rows written before 1.0 read as `cli`. **v0.9 cannot open a
  draft holding an 「Agent 代填」 rule, nor write a confirmation into a 1.0
  state file.**

## [0.9.0] — 2026-09-11

### Added

- Budgets a maintainer sets and nothing else can raise (`budget:` in
  `config.yaml`, ADR-011): statements per request (a confirmed run with its
  probe, or one agent question), statements and client-measured seconds per
  subject per business day, requests executing at once against one state
  file, and on ClickHouse the rows one statement may read (`max_rows_to_read`,
  enforced by the engine; refused at load on MySQL and SQLite, which cannot
  enforce it). `flow` admits a run after every check that needs no database
  and before the idempotency claim, so a refused run touches nothing and
  spends no key; a replay answers from the stored run whatever the
  allowance. `ask` and `chat` admit each statement and tell the model when
  the budget is spent. A spent allowance exits 2, a full concurrency slot
  75. Without the section nothing changes.
- The confirmation sheet warns about missing days before anyone confirms
  (ADR-010). By default from a cadence a maintainer declares on a mapping
  (`freshness: {lag_days: N}`), with no query at all; with
  `workflow.freshness_before_confirm: probe` the compiler's own
  `MAX(time_column)` probe may run before confirmation — short timeout,
  cached per table, charged to the budget. The note is advice, not part of
  the 口径: not stored, not hashed, and the result still reports the probe
  taken when the query ran. A run records what the cadence expected, and the
  result names data further behind than declared.
- 历史选择: asking about a metric again offers the choices you confirmed on
  your last successful run of it in the same workspace — the reading, an
  adopted document wording, a gap in your own words — dated, hashed, and
  filling only what is still open (ADR-012). Never the period, the split or
  the filter; never another subject's; never over a reading the documents
  select (shown beside it as 上次的选择). It lapses, without saying which
  document, when the mapping that ran has changed (each run now records a
  fingerprint of it), the option is gone, an adopted document no longer
  checks out, or it is older than `workflow.history_max_age_days` (90). Not
  offered with `--yes`; `--no-history` turns it off.
- 取值过滤: 「广告渠道的新增用户」 counts one value of a dimension whose
  mappings file declares `values:` — a closed set, with the words a question
  uses for each. Confirmed as 本次约定, hashed, compiled as `column = ?` with
  the value bound. A value nobody declared, two values or two dimensions are
  asked about, since a bound value matching nothing would read as 0;
  「各渠道」 and 「渠道分布」 are not filters. `--filter` states or replaces one
  (`none` for every value). The demo mappings declare values for 渠道 and 地区.

### Changed

- Invariant I2 now reads "no *business* query before confirmation"
  (ADR-010). In the default `declared` mode nothing at all runs before
  confirmation, as before.
- The state file gains `budget_leases`, `budget_ledger` and `freshness_cache`
  tables and two `runs` columns (`expected_through`, `mapping_fingerprint`),
  added automatically. v0.9 opens every v0.8 state file; **v0.8 cannot open
  a draft holding a 历史选择 rule** (a new `RuleSource`).

## [0.8.0] — 2026-09-11

### Added

- The result says how far the data reaches. After confirmation, each run
  of a structured mapping also reads `MAX(time_column)` from its table and
  records the newest record's date. When the period runs past it, the result
  names the missing days and what the number actually covers; when the
  whole period lies after it, an empty or zero result is explained as no
  data yet rather than as the business doing nothing. A failed probe is
  reported as unknown and never costs the result.
- 分组方式: 「每天」, 「每周」, 「每月」, or words for a dimension a
  maintainer declares per table in the mappings file (`dimensions:`, e.g.
  「各渠道」) split the result. Confirmed as 本次约定 like the period, bound
  into the hash, and compiled into `GROUP BY` with one expression per
  dialect. Over a confirmed period every day, week or month is listed —
  「无记录」 inside the data, 「无数据」 after it — and partial first or last
  weeks and months are said to be partial. 「日均」, 「每小时」 and two
  different splits are asked about instead of approximated; `--group-by`
  states or replaces one (`none` for one total). Documents cannot set it,
  a dimension not declared for a mapping's table is refused, not joined,
  and a split by something no maintainer declared (「各城市的」) is asked
  about rather than answered with a total.
- Document rules are checked against what runs. A structured mapping may
  declare `enforces:` — the rule keys its SQL applies and the words a
  handbook would use for them. A document rule whose verified quote contains
  a reading's words corresponds to it: the sheet marks it 「已由所选口径执行」
  or 「与所选口径不一致」, the result line counts applied rules as part of
  what ran, and contradicted ones are named under the result. When the
  documents agree on one reading the draft arrives with it chosen, marked
  「文档依据」 with its citation; adopting one side of a disagreement chooses
  its reading; a `--variant` contradicting the adopted wording is refused,
  while `--variant` on its own may overrule a handbook, visibly. Documents
  still never become SQL — they choose among statements a maintainer wrote.
  A quote naming two readings claims neither.

### Changed

- The dates of a confirmed 统计区间 are bound as parameters instead of being
  written into the SQL text (ADR-009, superseding ADR-008).
  `Connector.execute` takes `params=()` with `?` placeholders; MySQL and
  ClickHouse connectors translate them for their drivers and double the
  statement's other `%` signs. Calls without params are unchanged. Runs
  record the values beside the statement, and `flow` prints both. State
  files from v0.7 are upgraded in place.

## [0.7.0] — 2026-09-10

### Added

- 统计区间: the time a question names — 「上个月」, 「本周」, 「最近7天」,
  「2026-08」, an explicit range — is resolved to absolute dates when the
  draft is prepared, shown as 本次约定 with the words it came from, bound into
  the content hash, and compiled into the SQL. Two different periods, or an
  impossible date, are asked about rather than guessed. `--period` states or
  replaces one; a metric can require one with `required_rules: [period]`;
  `workflow.timezone` decides which day is today. Documents cannot set it.
- Structured mappings (`from` / `measure` / `label` / `time_column` /
  `where`) so a period can be applied. A whole-statement `sql:` mapping still
  runs, but refuses a period instead of answering it with all-time data.
  Values are typed, not bound (ADR-008): maintainer fragments and parsed
  dates are the only things that reach the statement.
- The result line names the period that ran, says 「未限定（全部数据）」 when
  there was none, and says a result is empty rather than printing a bare
  NULL or implying 0.

## [0.6.0] — 2026-09-10

### Added

- Document evidence: `queryagent kb import` indexes Markdown and DOCX (PDF
  via `pip install -e ".[docs]"`), and `flow` drafts 口径 from what the
  asking identity is allowed to read. Rules drawn from documents are marked
  「文档依据」 and carry file, section and line. Two documents disagreeing
  appear side by side under 「文档之间的分歧」, each with its citation, and
  nothing runs until the user adopts one (`--adopt counting_basis:0`) —
  recorded as 本次约定, keeping that document's citation. A rule a metric
  declares in `required_rules` that no document states is listed as missing
  and has to be written down by the user (`--rule time_window=按自然月统计`);
  nothing defaults it. Evidence is
  re-checked before confirming and before executing, and a withdrawn or
  edited source expires the draft without changing its version or hash.
- The model cannot fabricate a citation: it selects an index into a menu the
  server built from authorised chunks, and every surviving rule must quote
  its chunk verbatim, with the offsets computed server-side and every number
  in the rule present in the quote. What it cannot do is prove the quote
  *supports* the rule — that judgement stays with the reader, which is why
  the quote and its location are on the sheet.
- The result line names only the reading the query executed. Document rules
  and 本次约定 explain the 口径 but are not compiled into SQL — the maintainer
  mapping is what runs — so they are listed in a note saying the two are not
  cross-checked, rather than presented as the number's definition.
- Semantic retrieval as an option (`knowledge.embedding` plus
  `QUERYAGENT_EMBEDDING_API_KEY`, any OpenAI-compatible `/v1/embeddings`): no
  vector database, no numpy, off unless configured, and it says so when it
  degrades to keyword. `kb import` embeds, and says where the text was sent.
  On a fixed paraphrase set Recall@3 is 9/13 for keyword and 12/13 for
  BAAI/bge-m3; on questions the corpus cannot answer, false evidence is 0/8
  and 1/8. The similarity floor is configurable because it belongs to the
  model; its 0.5 default was chosen on that same set, so 1/8 is in-sample.
- `queryagent flow` (slice 1A): a confirmation-gated query path. It prepares a
  structured 口径 from the declared metrics, shows it with every rule marked
  文档依据 / 系统映射 / 本次约定, and executes only after an explicit
  confirmation stored server-side and bound to the draft's version and
  content hash. Amending the 口径 invalidates the earlier confirmation;
  repeating a request with the same idempotency key returns the first run
  rather than querying again; a confirmed 口径 with no maintainer-declared
  mapping is refused rather than guessed.
- `metrics.yaml` gains an optional `variants:` list — the competing readings
  a `caution` describes in prose, made selectable so a user can choose one
  and a confirmation can bind to that choice. Required fields are unchanged.
- `query_mappings.yaml` (`workflow.mappings_path`): the maintainer-declared
  口径 → SQL table `flow` executes from. Nothing else is executable.

### Fixed before release

- `amend()` accepted rules claiming any provenance, so a caller could label
  its own convention 「文档依据」 with a citation pointing nowhere. Not
  reachable through the CLI, which hardcodes USER, but `amend` is the API a
  Web or MCP entry point calls.
- The credential-key rejection lived inside the LLM config loader, so every
  new config section silently opted out of it.
- Two documents disagreeing on a rule the maintainer had not declared
  required were silently dropped in `flow`: adding a second team's handbook
  made the cited counting basis disappear from the sheet. The one test of
  this behaviour passed a required key; `flow` passes none.
- The line under a result listed document rules the executed SQL did not
  apply — 「统计周期=按自然月」 above an all-time COUNT.
- `required_rules` had been specified but never implemented, so "a rule the
  documents do not state is listed as missing" could not happen in `flow`.
- The extraction prompt named rule keys without defining them, and the model
  filed an attribution date under time_window, filling a gap the user should
  have been asked about. Keys are now defined in the prompt — a mitigation,
  not a guarantee.

Scope, stated plainly. Document ACLs are per business workspace, not per
subject. There is no query budget. Workflow and index state are local SQLite
files for a single process. No OCR, no incremental sync, no reranker.

## [0.5.1] — 2026-09-09

### Fixed

- Recover JSONL logs with partial UTF-8 tails; isolate unfinished records
  before appending, and reject unsigned checkpoints for a real resumed run.
- Resume identity now includes case contents, effective settings, metrics,
  local data snapshots, date and implementation. Remote-data resume requires
  an operator-supplied `--data-version`; credentials are never recorded.
- Parallel eval persists completed cases immediately, bounds in-flight work,
  stops submitting after an outage and saves measured in-flight results.
- MySQL refuses SQL if setting its server timeout fails, bounds I/O and pool
  waits, recovers pool capacity after failed reconnects, and streams capped
  results without draining the remainder on truncation.

- Preserve retryability before formatting provider exceptions: a network
  connection failure during eval exits 75, not a misleading balance/key error.

### Evaluation clarification

- Scoring v2 separates query-trajectory hits from normal completion with a
  SQL hit. Neither measures natural-language answer correctness. First-query
  scoring is no longer invalidated by a later failed query; truncated row
  sets cannot prove full equality. Old reports retain their original values.
- The earlier 3m29s/22m speed claim compared unequal successful workloads
  (64 requests in the fast run were refused) and is withdrawn as a benchmark.
- The historical sample-size and causal claims below are not general
  guarantees. Similar new sample scores do not prove old gains were noise;
  small three-cell comparisons do not establish an entire causal effect.
  Current README and evaluation rules state these limitations explicitly.

## [0.5.0] — 2026-08-22

### Added

- **A public API.** `queryagent` exports the agent loop, the event types,
  the wiring pieces and the exception hierarchy with an explicit `__all__`;
  the README gained a library-usage section whose snippet is executed by the
  test suite. The package called itself a library while
  `from queryagent import *` returned nothing.
- **`--concurrency N` for eval** — 100 cases finished in 3m29s against 22
  minutes serially. Each worker thread owns its connector: SQLite's timeout
  guard lives on the connection, so sharing one lets concurrent queries strip
  each other's deadline.
- `trace_dir` in config, and the startup notice prints an absolute path.

### Changed

- **A refused request is now "unmeasured", not a wrong answer.** A run whose
  provider balance ran out scored 64 of 100 cases as failures and reported
  "14%" — a number that looks like a measurement and means the account ran
  out of money. Retryability and measurability are now separate questions
  with separate functions, and an aborted run exits 75 for an outage but 2
  for a refusal, since telling a retry loop to wait on an empty account would
  spin forever.
- **Clarify and metric-citation rates got real denominators**: clarify 2→8
  cases, must-not-ask controls 2→8, metric citation 4→8. Four more metrics
  gained a `caution` so ambiguity has more than one shape. At four cases,
  "4/4" was a good-looking number with almost no evidence behind it; at
  sixteen the clarify result held (15–16/16 across three runs).
- Offset-aware datetimes normalise to UTC before comparison — 12:00Z and
  12:00+08:00 previously compared equal.
- `__version__` comes from package metadata rather than a second literal that
  had already drifted to 0.1.0, and every runtime dependency has an upper
  bound after `anthropic` 1.0 turned CI red without a line of our code
  changing.
- Chat keeps the 20 most recent turns in memory instead of every turn.

### Documented

- **How far each backend is actually verified.** Every published number, live
  smoke test and failure analysis came through the OpenAI-compatible backend
  against DeepSeek. The Anthropic backend has contract tests but has never
  made a live call, and was broken against `anthropic` 1.x until CI caught
  it. `llm.temperature` has no effect there — the Messages API dropped the
  parameter — so the backend warns rather than letting a run believe it was
  deterministic.

## [0.4.0] — 2026-08-20

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

On the new samples (`deepseek-v4-flash`, temperature 0): dev 39% first
execution / 49% after self-repair (100 cases); sealed test 32% / 48% (200
cases).

**The larger samples corrected an earlier claim of ours.** At 30 cases per
set, v0.3.0 measured a +14pp dev gain against a +6pp test gain and described
the gap as an overfitting measurement. At 100/200 cases the two sets agree
within 1pp, so that gap is best explained as noise — which is precisely what
the power analysis predicted (±25pp for a difference at n=30) and precisely
why the samples were expanded.

A controlled decomposition
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
  language + seam map).

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
