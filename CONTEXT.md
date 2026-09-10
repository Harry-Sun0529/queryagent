# CONTEXT — domain language & seam map

For humans and agents working on this repo. ADRs live in `docs/adr/`;
specs for in-flight work in `docs/specs/`.

## Domain language

- **Metric（口径）** — a named business definition of a number
  (`metrics.yaml`). The same everyday phrase ("新增用户") can map to
  *competing* definitions; a metric with a `caution` field declares that
  conflict.
- **Clarify** — the agent asking the user one question instead of guessing
  between competing metric definitions. Emitted as a terminal
  `ClarifyEvent`; never triggered when the question already disambiguates.
- **Question / conversation / history** — one `run_agent` call answers one
  *question*; *history* is that run's tool exchanges; *conversation* is the
  finished prior turns of a chat session (plain text pairs).
- **Self-repair** — failed SQL comes back as an error observation the model
  reads and fixes; capped by `max_retries`.
- **Case / anchor** — eval cases are self-built (iterated on) or public
  anchor (BIRD, split into an analysable dev set and a sealed test set —
  ADR-004).
- **Unmeasured** — a case the provider could not be reached for. It is not a
  wrong answer: it leaves the pass-rate denominators, is never written to the
  resume log, and five consecutive completions stop new submissions. Measured in-flight
  results are saved before exit.
- **Variant（口径取法）** — a maintainer-declared competing reading of one
  metric (`variants:` in `metrics.yaml`). `caution` is the same disagreement
  as prose for a model to read; a variant is it made *selectable*, so a user
  can pick one and a confirmation can be bound to the choice.
- **Draft（口径确认单）／Confirmation／Run** — the workflow layer's three
  records. A draft is a versioned structured 口径 belonging to one subject; a
  confirmation is proof that subject approved one exact draft *version and
  content hash*; a run is one execution against a confirmation. No valid
  confirmation, no business SQL — this is stronger than **Clarify**, which is
  a model decision the model can decline to make.
- **Provenance（来源标注）** — every rule records whether it came from a
  document, the maintainer's config, or the user's own agreement this time
  (文档依据／系统映射／本次约定). Collapsing these is the failure mode the
  product exists to prevent.
- **Evidence / citation（证据／引用）** — a chunk of an indexed document plus
  where it sits (file, section, line). A rule marked 「文档依据」 carries one.
  The model never emits a citation: it picks an index into a menu the server
  built from what this subject may read, so a fabricated one is not
  expressible rather than caught.
- **Workspace（业务空间）** — the unit document permission is granted in.
  Scoping happens in the retrieval query, not after it: text filtered out
  afterwards has already been in the process that builds the prompt.
- **Mapping（映射）** — the maintainer-declared 口径 → SQL table
  (`query_mappings.yaml`). A confirmed 口径 with no mapping is refused, not
  guessed.
- **Disagreement（文档之间的分歧）／Required rule（必需规则）** — two
  documents stating a rule differently become two cited readings; nothing
  runs until the user adopts one, and the adoption is 本次约定 citing that
  document. A metric's `required_rules` are gaps until a document states them
  or the user writes them down. Neither changes the SQL: documents explain,
  mappings execute.
- **Period（统计区间）** — the absolute date range a draft is bounded to,
  resolved from the question's time words (or stated with `--period`) when
  the draft is prepared, and hashed with it. Only the user sets it; documents
  cannot. With the variant and the grouping, it is one of the three rules the
  compiler consumes; its dates are bound as parameters (ADR-009).
- **Grouping（分组方式）** — whether the answer is one number or a table, and
  split how: by day, week (Monday-start) or month, or by a **Dimension** a
  maintainer declares per table in the mappings file. Read from the
  question's words or `--group-by`, hashed, user-only like the period.
  「日均」 is not a grouping and is asked about.
- **Data reach（数据新鲜度）** — the date of the newest record in a mapping's
  table, probed after confirmation and recorded on the run. It is all the
  system claims: not that the data is complete up to that day.
- **Trace** — one run's event stream persisted as JSONL, replayable
  (ADR-005). **Checkpoint** — the eval's per-case result log, which
  `--resume` reuses when the effective input/data/code signature matches.
- **SQL hit / completion** — a trajectory may contain a correct SQL query
  without ending successfully. Scoring v2 reports them separately; neither
  proves natural-language answer correctness.

## Seam map (where the interfaces are)

| Seam | Interface | Adapters today |
|---|---|---|
| LLM | `LLMBackend.complete(messages, tools) -> ModelResponse` | OpenAI-compatible (DeepSeek — the verified path), Anthropic (contract-tested only, never called live), test fake |
| Data source | `Connector.get_schema/execute/close` (+ `dialect`); `execute(..., params=())` binds `?` placeholders | MySQL, SQLite, ClickHouse |
| Metrics | `MetricStore.match/get` | YAML store (embedding impl reserved) |
| Agent output | `Iterator[AgentEvent]` from `run_agent` | chat CLI, ask CLI, eval runner, trace writer |
| Persisted records | `serde.rebuild_dataclass` | trace events, eval checkpoints |
| Tool dispatch | `ToolRegistry.validate_and_dispatch -> Observation` | get_schema, execute_sql, ask_clarification |
| Draft building | `DraftBuilder.build(question, actor) -> BusinessDefinition` | maintainer metrics; maintainer + document evidence (`CompositeDraftBuilder`) |
| Document evidence | `KnowledgeProvider.search/read/check_refs(scope, ...)` | local SQLite index, keyword or optional semantic |
| Plan compiling | `TemplateCompiler.compile(definition) -> CompiledQuery(sql, params)`; `freshness_probe(definition)` | structured maintainer mappings + bound period (ADR-009) + time or declared-dimension grouping; whole-statement `sql:` kept, refuses a period or a grouping and is not probed |
| Workflow state | `SqliteWorkflowStore` (drafts / confirmations / runs) | local SQLite file, single process |
| Trusted identity | `ActorContext(subject_id, workspace_id, roles)` | CLI local user (Web session / MCP host reserved) |

Rules that keep the seams honest: agent code never touches provider SDK
types; renderers never live in `agent.py`; tool failures return error
`Observation`s (only `SafetyViolation` raises — it terminates the run);
new database = new `Connector` file, nothing else changes; anything written
to disk must survive being read by a different version and by a process that
was killed mid-write.

## Two paths, deliberately separate

`ask`/`chat` run the ReAct loop: the model proposes SQL and executes it
directly. `flow` runs the workflow layer: nothing reaches the database
without a stored confirmation bound to the exact 口径 the user read. They
share the connector and safety layer and nothing else. The gate is only
worth anything if it cannot be walked around, so `flow` does not fall back
to the agent loop when it has no mapping — it refuses.

## Exit codes (ADR-006)

`2` the user's environment or input · `70` a defect in QueryAgent · `75`
upstream trouble, retryable · `130` interrupted.

## Safety model

Three independent layers (see `SECURITY.md`): sqlparse whitelist
(`safety.py`) → connector timeout/row caps → read-only DB account.
