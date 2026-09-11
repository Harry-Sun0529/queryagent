# QueryAgent

[![CI](https://github.com/Harry-Sun0529/queryagent/actions/workflows/ci.yml/badge.svg)](https://github.com/Harry-Sun0529/queryagent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**Zero-infrastructure Text-to-SQL agent for small data teams and individual
data engineers.** `pip install`, point it at your database, ask questions in
natural language. Business metric definitions live in one YAML file that goes
into git — reviewing a metric change is just reviewing a PR. And when metric
definitions conflict, the agent **asks you instead of guessing**.

```text
# illustrative session (numbers depend on the generated demo data)
你问> 上个月新增用户有多少？

[?] “新增用户”有两种口径：注册口径（按 created_at）和运营口径（按首单时间
    first_order_at），你要哪一种？
你答> 注册口径

[ANSWER] 按注册口径，上个月新增用户 8,377 人（已剔除内部测试账号）。
SQL: SELECT count(*) FROM users WHERE strftime('%Y-%m', created_at) = ...
```

## Why another Text-to-SQL tool?

On the complexity spectrum *Vanna (train a RAG model first) → WrenAI (deploy
a multi-service platform) → DB-GPT (orchestrate multiple agents)*, QueryAgent
takes the leftmost position: **no services, no UI, no agent framework, and
no vector store in the base install**. One process, one `config.yaml`, one
`metrics.yaml` — plus, optionally, a directory of documents and a local
SQLite index (see [Document evidence](#document-evidence)).

|  | Vanna | WrenAI | QueryAgent |
|---|---|---|---|
| Setup before first answer | train a RAG model | deploy multi-service platform + build MDL | write one config.yaml |
| Semantic / metric layer | none formal (example retrieval) | MDL (full-featured, JSON) | one YAML file, git-diffable |
| Infrastructure | vector store | services + vector store + UI | **none** (a local SQLite file if you index documents) |
| Conflicting metric definitions | — | governed centrally | **agent stops and asks you** |
| Form factor | library | BI platform | library |
| License | MIT | AGPL-3.0 engine | MIT |

WrenAI solves enterprise governance ("the CFO and the PM must get the same
number"). QueryAgent solves the engineer's problem: *make the agent use my
definitions today, with zero new infrastructure*. Lightness is the feature.

## Features

- **Hand-written ReAct loop** — no LangChain/LlamaIndex; the whole control
  flow is one readable generator with five explicit termination conditions,
  parse-failure fallback, and a self-repair loop (database errors are fed
  back to the model, capped at 3 retries). Multi-turn chat keeps the session
  in context, so follow-ups can refer back.
- **Observability**: every run records its event stream to
  `.queryagent/traces/*.jsonl`; `queryagent replay <trace>` reconstructs it
  exactly. Token usage, prompt-cache hit rate, latency and an upper-bound
  cost estimate are reported per run and per eval suite. On by default with
  a startup notice and an off-switch ([ADR-005](docs/adr/005-traces-on-by-default.md)).
- **Metrics as YAML** (`metrics.yaml`): definitions are matched to the
  question and injected into the prompt; answers cite the metric used. With
  a knowledge base configured, `flow` adds rules drawn from your documents,
  each carrying the file, section and line it came from.
  Metrics with a `caution` field trigger a **clarifying question** when the
  user's phrasing is ambiguous — and are forbidden from asking when it isn't.
- **Confirmation-gated queries** (`queryagent flow`): the same question can
  mean two different numbers, so the flow shows a structured 口径 —
  each rule marked 文档依据 / 系统映射 / 本次约定 — and runs nothing until
  the user confirms it. The confirmation is stored server-side and bound to
  the draft's version *and* content hash: amend the 口径 and the old
  confirmation stops matching. A confirmed 口径 with no maintainer-declared
  mapping is refused rather than guessed. This path shares no execution
  route with `ask`/`chat` — see [CONTEXT.md](CONTEXT.md). The period a
  question names — 「上个月」, 「最近7天」, 「2026-08」 — is shown as absolute
  dates, bound into the confirmation and compiled into the SQL; a period it
  cannot resolve is asked about, not guessed.
- **Three-layer SQL safety**: a token-level whitelist (single SELECT only,
  CTEs allowed — string literals can't fool it, comments can't smuggle past
  it), connector-enforced timeouts and row caps, and a documented read-only
  account setup as the final backstop. See [SECURITY.md](SECURITY.md).
- **Three dialects out of the box**: MySQL, SQLite (stdlib, Docker-free
  demo), ClickHouse (`pip install queryagent[clickhouse]`). New sources
  implement one 3-method protocol.
- **Two providers, one abstraction**: any OpenAI-compatible endpoint
  (DeepSeek / Qwen / GLM / vLLM / Ollama) via `base_url`, plus Anthropic.
  Provider tool-call formats never leak into the agent. **Verification is
  not equal between them** — see the note below.
- **Event-stream architecture**: the agent yields `AgentEvent`s; the CLI,
  the eval runner, and any future UI are just different consumers. This is
  the load-bearing seam of the codebase.
- **Reproducible evaluation built in**: `queryagent eval` runs a 36-case
  self-built suite (including should-ask / must-not-ask clarify controls)
  plus a fixed-seed public-benchmark subset (BIRD/Spider), comparing
  executed result sets — never SQL text. See [eval/README.md](eval/README.md).

## Quickstart (SQLite — no Docker, ~2 minutes)

```bash
git clone https://github.com/Harry-Sun0529/queryagent && cd queryagent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make demo-data                        # generates demo_shop.db (fictional e-commerce)
export OPENAI_API_KEY=sk-...          # DeepSeek key works here (default config)
queryagent chat --config examples/demo_ecommerce/config.sqlite.yaml
```

Try: `上个月每天的新增用户数` — and watch it ask which definition of
"new user" you mean, then keep the thread: follow up with `那按渠道拆分呢？`
and it remembers the month and the definition you chose. `--verbose` shows
the full THINK / ACT / OBSERVE trace. For scripts and pipes there is a
one-shot form:

```bash
queryagent ask "上个月的成交额是多少？按支付口径" \
    --config examples/demo_ecommerce/config.sqlite.yaml
```

The default configs talk to DeepSeek via the OpenAI-compatible backend; the
same backend reaches Qwen/GLM/OpenAI/vLLM/Ollama by changing `base_url`.
With an Anthropic key, switch the commented `llm:` block:

```yaml
llm:
  backend: anthropic          # reads ANTHROPIC_API_KEY
  model: claude-sonnet-5
```

> **How far each backend is verified.** Everything published here — the
> numbers, the live smoke tests across three dialects, the failure analysis —
> was produced through the **OpenAI-compatible backend against DeepSeek**.
> The Anthropic backend has contract-level tests (message conversion,
> tool_use and tool_result blocks, usage parsing) but **has never made a call
> to the live API**, because the maintainer has no key. It was in fact broken
> against `anthropic` 1.x until CI caught it. Treat it as untried in
> production, and note that `llm.temperature` has no effect there: the
> Messages API dropped the parameter, and the backend warns rather than
> letting a run believe it was deterministic.

### Confirmation-gated flow

The same question, two 口径, two numbers — and nothing runs until you say so:

```bash
queryagent flow "上个月新增用户有多少？" --config examples/demo_ecommerce/config.sqlite.yaml
```

It prints the 口径 confirmation sheet, asks which reading you mean
(`registered` = by signup date, `first_order` = by first-order date), asks
you to confirm, and only then executes the maintainer-declared query for
that reading. Answer nothing at either prompt and it exits 2 having queried
nothing. `--variant` and `--yes` script the two answers; `--yes` automates
the human, it does not bypass the gate — the confirmation record is still
created and still bound to that exact draft version.

The time in the question is part of the 口径. 「上个月」 appears on the sheet as
「2026-08-01 至 2026-08-31（31 天）」, marked 本次约定 because you asked for it,
and is bound into the confirmation — a draft confirmed on 10 September still
runs August if it is executed in October — then compiled into the SQL as a
condition on the mapping's `time_column`. Two different periods in one
question, or one the parser does not recognise, are asked about rather than
guessed; `--period` states or replaces one (`--period 2026-08-01..2026-08-31`).
The dates are bound as parameters, not written into the SQL text
([ADR-009](docs/adr/009-bound-parameters-for-workflow-values.md)). The result
line names the period that ran, says 「未限定（全部数据）」 when there was
none, and says a result is empty instead of printing a bare NULL.

How the answer is split is part of the 口径 too. 「上个月每天的新增用户」
is confirmed as 「分组方式：按天」 and compiled into a `GROUP BY`; 「每周」
and 「每月」 work the same way, and 「各渠道」 splits by any dimension a
maintainer declares for the mapping's table (`dimensions:` in
`examples/query_mappings.yaml`). Every day of the period gets a line, so a
missing one cannot hide. 「日均」 is a different metric, not a split, and is
asked about, as is a split by something nobody declared (「各城市的」);
`--group-by none` asks for one total.

The result also says how far the data reaches. The demo data ends on
2026-08-22, so 「上个月」 asked in September is reported as covering 1–22
August with the last 9 days named as having no data, and 「本月」 as having
no data yet rather than a total of 0. That check is a query, so it runs
after you confirm, never before.

### Document evidence

Point `flow` at your handbooks and the confirmation sheet starts citing them:

```bash
queryagent kb import --config examples/demo_ecommerce/config.sqlite.yaml
```

```bash
queryagent flow "上个月新增用户有多少？" --config examples/demo_ecommerce/config.sqlite.yaml --workspace ops
```

Rules extracted from documents are marked 「文档依据」 and carry the file,
section and line, so the reader can open the source and check. Where two
documents disagree, both readings appear under 「文档之间的分歧」 with their
own citation, neither is chosen for you, and nothing runs until you adopt one
(`--adopt counting_basis:0`); your choice is marked 本次约定 and keeps the
citation. A rule a metric declares in `required_rules` that no document
states is listed as missing, and you write it down
(`--rule time_window=按自然月统计`) rather than the system defaulting it. The
demo config puts a growth-team handbook in the same workspace as the ops one,
so the disagreement shows up on the first run.

Document text never becomes SQL; what executes is always a maintainer's
mapping. But a mapping can declare which rules its statement applies and the
words a handbook would use for them (`enforces:` in
`examples/query_mappings.yaml`), and then document rules are checked against
what runs. A rule whose quoted sentence contains a reading's words is marked
「已由所选口径执行」 and counted in the result line, or 「与所选口径不一致」
and named under the result. When the handbooks agree on one reading, the
draft arrives with it chosen, marked 「文档依据」 with its citation; adopting
one side of a disagreement chooses that side's reading; `--variant` can
still overrule a handbook, and the conflict is shown. The match is by
declared words, not by meaning: a quote naming two readings claims neither,
and rules nothing matched stay in a note saying they were not checked.

Documents are scoped to a business workspace: an identity in one workspace
does not retrieve — not "does not display" — another's. Document text is
data, never instruction: it reaches the model inside a delimited block, on a
call made with no tools at all, and what executes is still only a
maintainer-declared mapping.

Retrieval is keyword-based out of the box and needs no new dependency.
Semantic retrieval is optional, off unless configured, and speaks the
OpenAI-compatible `/v1/embeddings` protocol (`QUERYAGENT_EMBEDDING_API_KEY`)
rather than embedding a vector database. **Enabling it sends document text
to that endpoint** — a data-boundary decision for whoever deploys it. See
[ADR-007](docs/adr/007-document-evidence-retrieval.md).

Measured on a fixed paraphrase set (13 questions) and on questions the
corpus cannot answer (8), k=3
([evidence](eval/results/retrieval-2026-09-10-floor-0.50/README.md)):

| mode | Recall@3 | false evidence on unrelated questions |
|---|---:|---:|
| keyword | 9/13 | 0/8 |
| semantic (BAAI/bge-m3, floor 0.5) | 12/13 | 1/8 |

Semantic retrieval recovers three of the four zero-literal-overlap synonyms
keyword misses, and pays for it in false evidence. The similarity floor is a
property of the embedding model and is configurable; the 0.5 default was
chosen after seeing the unrelated-set scores, so the 1/8 is in-sample. At
the 0.35 that passed every stub test, 6 of 8 unrelated questions retrieved
"evidence". Twenty-one questions and one run support no statistical claim.

### MySQL / ClickHouse (Docker)

```bash
make demo-up      # MySQL 8 on :3307, data pre-loaded, read-only account
queryagent chat --config examples/demo_ecommerce/config.yaml

make demo-up-ch   # additionally ClickHouse on :9001
queryagent chat --config examples/demo_ecommerce/config.clickhouse.yaml
```

### Using it as a library

The CLI is one consumer of the event stream; your code can be another. The
public surface is what `queryagent` exports — everything else may move.

```python
from queryagent import AnswerEvent, ContextBuilder, ToolRegistry, run_agent
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.llm import make_backend
from queryagent.schema import render_schema
from queryagent.tools import make_default_tools

connector = SQLiteConnector(path="examples/demo_ecommerce/demo_shop.db")
builder = ContextBuilder(
    schema_text=render_schema(connector.get_schema()), dialect=connector.dialect
)
registry = ToolRegistry(make_default_tools(connector, timeout_s=10, max_rows=200))

for event in run_agent("有多少用户？", backend=backend, registry=registry,
                       context_builder=builder):
    if isinstance(event, AnswerEvent):
        print(event.text)
```

This snippet is executed by `tests/test_public_api.py` — documented code
that was never run is how a library's first impression breaks.

### Your own database

Create a **read-only** account (this is a load-bearing part of the security
model, not optional hardening):

```sql
CREATE USER 'queryagent_ro'@'%' IDENTIFIED BY '...';
GRANT SELECT ON your_db.* TO 'queryagent_ro'@'%';
```

Point `config.yaml` at it, write a `metrics.yaml` for your business
definitions, and set `metrics_path` in the config.

## Defining metrics

```yaml
metrics:
  - name: new_users              # required, unique
    display_name: 新增用户
    aliases: [新用户, new users]
    definition: >                # required — injected into the prompt
      按 users.created_at 的日期计数（注册口径）；不含测试账号。
    caution: >                   # optional — makes ambiguity a question, not a guess
      运营口径按 first_order_at 计数；未指明口径且涉及报表时需确认。
    tables: [users]              # optional
    sql_hint: "COUNT(*) FROM users WHERE ..."   # optional
```

Required fields (`name`, `definition`) are frozen; optional fields may grow
(semver promise, see [CHANGELOG.md](CHANGELOG.md)).

## Evaluation

```bash
make eval                                     # self-built 36 cases, demo db
queryagent eval --model deepseek-v4-pro \
  --config examples/demo_ecommerce/config.sqlite.yaml    # strong-model run

queryagent eval --public eval/public/dev-subset.json \
  --db-dir eval/public/databases \
  --config examples/demo_ecommerce/config.sqlite.yaml    # BIRD dev set
```

Methodology: executed row sets compared as order-insensitive multisets with
float tolerance; six metrics including **clarify-behaviour accuracy**
(asked when it should, didn't when it shouldn't). A fixed-seed subset of a
public benchmark serves as an external anchor, with a hard rule that prompts
are never tuned against it ([eval/README.md](eval/README.md)).

### Reliability repair measurements (2026-09-09, scoring v2)

Four complete dev100 runs (serial/parallel/parallel/serial) measured SQL
trajectory hits of 43/43/47/44 and completed SQL hits of 43/42/46/42.
Concurrency 4 took about 9 minutes versus 24–26 minutes at concurrency 1
(2.73× ratio of mean wall times). This supports optional `--concurrency 4`
for this local offline eval; the default stays 1. Repeated runs changed
individual outcomes, so this is not evidence of statistical equivalence or
natural-language answer correctness. [Full measurements and limitations](eval/results/reliability-2026-09-09-rerun/README.md).

### Historical results (through v0.5.0, `deepseek-v4-flash`, temperature 0)

These published numbers use the **legacy scorer**: any executed SQL matching
the reference counted as a pass, even if the run later failed or its final
answer was wrong. They are retained as historical query-trajectory measurements,
not final-answer accuracy. New reports use scoring v2 and are not directly
comparable for first-execution rate. See [evaluation rules](eval/README.md).

**Self-built suite** (36 cases, ranges over 3 runs — DeepSeek exposes no
sampling seed; one run does not establish a stable rate):

| metric | `deepseek-v4-flash` |
|---|---|
| first-execution pass rate | 20–23/28 (71–82%) |
| pass rate after self-repair | **26–27/28 (93–96%)** |
| metric-citation rate | 6–8/8 |
| **clarify-behaviour accuracy** | **15–16/16 (94–100%)** |

Clarify accuracy counts both arms: the eight questions that *should* draw a
question, and the eight that must **not** — a system that asks about
everything can score 8/16 if it names the expected metrics on all should-ask cases. The denominator was four until v0.5.0,
where "4/4" was a good-looking number with almost no evidence behind it;
quadrupling it left the result standing.

An earlier strong/weak comparison used a smaller case set. It observed similar
query-trajectory hit rates at different costs, but does not establish equal
final-answer accuracy or isolate the causal contribution of the architecture
([historical analysis](eval/results/dual-model-analysis.md)).

**Public benchmark** (BIRD mini-dev, dev/test split — [ADR-004](docs/adr/004-public-subset-external-anchor.md)):

| | dev (100 cases, analysed) | test (200 cases, sealed) |
|---|---|---|
| first-execution pass rate | 39% | 32% |
| pass rate after self-repair | **49%** | **48%** |
| tokens / latency / cost per case | 9,612 / 12.4s / $0.0022 | 8,699 / 11.8s / $0.0019 |

Honest notes, in the order they matter:

- **Statistical limits.** The old dev +14pp / test +6pp gains were not a
  controlled estimate of overfitting. Nor does the newer 49% / 48% final-score
  comparison prove the earlier gap was noise: these are different quantities
  on different samples. We withdraw both causal interpretations.
- Paired comparisons depend on the target effect and discordant outcomes;
  there is no universal “57–114 cases is enough” threshold. Power must be
  planned for a specific experiment. Small or similar observed rates do not
  establish equivalence.
- **The sealed set stays sealed.** The governing rule is *never change the
  system in response to test results* — not "run it once". It ran once this
  release, on 200 questions freshly sampled from those never used before.
- **Where the remaining failures are** (from dev analysis at the previous
  size, still the operative picture): half were shape rather than substance —
  the right value returned with extra columns — and one general prompt rule
  fixed that class; a quarter are gold-SQL ambiguities that should not be
  fixed; a quarter are genuine capability gaps
  ([dev-failure-analysis.md](eval/results/dev-failure-analysis.md)).
- A [historical three-cell comparison](eval/results/version-decomposition.md)
  observed changes associated with code and thinking mode on a small sample.
  It does not establish that the entire historical difference was caused by
  one variable, or reproduce an old provider model snapshot.
- Costs are peak-rate upper bounds (off-peak is half). Raw reports:
  [eval/results/](eval/results/).

## Architecture

Two entry paths, sharing the connector and safety layer and nothing else.

```
queryagent flow ──▶ QueryWorkflow (workflow/) ──▶ draft ──▶ confirmation ──▶ run
                        │                         (versioned, hashed, persisted)
                        ├─ MetricDraftBuilder      口径 candidates + gaps
                        ├─ TemplateCompiler        maintainer mapping only
                        └─ SqliteWorkflowStore     local, single process
                                    │
                                    └──▶ safety.py ──▶ Connector

question ──▶ ReAct loop (agent.py) ──▶ Iterator[AgentEvent] ──▶ consumers
                 │                                              (chat CLI,
                 ├─ LLMBackend        llm/          Anthropic | OpenAI-compat
                 ├─ ToolRegistry      tools.py      get_schema | execute_sql
                 │                                  | ask_clarification
                 │      └─▶ safety.py ─▶ Connector  connectors/  mysql | sqlite
                 │          (whitelist)             | clickhouse
                 ├─ ContextBuilder    context.py    schema + metrics + budget
                 └─ MetricStore       metrics/      YAML store, alias matching
```

Every module is small enough to read in one sitting; there is deliberately
no framework between you and the control flow. Design rationale for the big
decisions lives in commit messages and [prompt-log.md](prompt-log.md) — this
project was built with heavy AI assistance under a documented protocol, and
the log is the honest record of who decided what.

## Development

```bash
make test        # ruff + mypy + pytest; DB integration tests auto-skip
                 # when demo containers are not running
make demo-down   # tear down demo databases
```

## Roadmap

- PostgreSQL connector (validates the Connector seam further)
- Per-subject document ACLs (today's scoping is per business workspace)
- Cross-session memory for confirmed metric choices
- Embedding-based matching as an optional MetricStore implementation
- Published eval numbers (strong + weak model, self-built + public subset)

## License

[MIT](LICENSE)

---

## 中文速览

QueryAgent 是给小数据团队和个人工程师的**零基建 Text-to-SQL Agent 库**：
不用训练、不用部署平台、不用向量库。业务口径写在一个 YAML 里进 git，改口
径就是发 PR；当口径之间冲突（比如"新增用户"既可以按注册也可以按首单）而
问题又没说清时，agent 会**停下来反问**而不是猜一个。

两分钟上手（免 Docker）：

```bash
pip install -e ".[dev]" && make demo-data
export OPENAI_API_KEY=...      # 示例配置默认使用 DeepSeek
queryagent chat --config examples/demo_ecommerce/config.sqlite.yaml
```

安全模型：SQL 白名单（仅单条 SELECT，词法级校验）+ 连接层超时/行数上限 +
只读数据库账号，三层互相独立。评估体系随库附带：`make eval` 一条命令复现
36 条自建用例（含"该问的要问、不该问的不许问"的追问对照组）。
