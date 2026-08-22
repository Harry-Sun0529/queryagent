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
  resume log, and five consecutive ones abort the run.
- **Trace** — one run's event stream persisted as JSONL, replayable
  (ADR-005). **Checkpoint** — the eval's per-case result log, which
  `--resume` reuses when the run signature matches.

## Seam map (where the interfaces are)

| Seam | Interface | Adapters today |
|---|---|---|
| LLM | `LLMBackend.complete(messages, tools) -> ModelResponse` | OpenAI-compatible (DeepSeek — the verified path), Anthropic (contract-tested only, never called live), test fake |
| Data source | `Connector.get_schema/execute/close` (+ `dialect`) | MySQL, SQLite, ClickHouse |
| Metrics | `MetricStore.match/get` | YAML store (embedding impl reserved) |
| Agent output | `Iterator[AgentEvent]` from `run_agent` | chat CLI, ask CLI, eval runner, trace writer |
| Persisted records | `serde.rebuild_dataclass` | trace events, eval checkpoints |
| Tool dispatch | `ToolRegistry.validate_and_dispatch -> Observation` | get_schema, execute_sql, ask_clarification |

Rules that keep the seams honest: agent code never touches provider SDK
types; renderers never live in `agent.py`; tool failures return error
`Observation`s (only `SafetyViolation` raises — it terminates the run);
new database = new `Connector` file, nothing else changes; anything written
to disk must survive being read by a different version and by a process that
was killed mid-write.

## Exit codes (ADR-006)

`2` the user's environment or input · `70` a defect in QueryAgent · `75`
upstream trouble, retryable · `130` interrupted.

## Safety model

Three independent layers (see `SECURITY.md`): sqlparse whitelist
(`safety.py`) → connector timeout/row caps → read-only DB account.
