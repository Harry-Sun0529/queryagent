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
takes the leftmost position: **no vector store, no services, no UI, no agent
framework**. One process, one `config.yaml`, one `metrics.yaml`.

|  | Vanna | WrenAI | QueryAgent |
|---|---|---|---|
| Setup before first answer | train a RAG model | deploy multi-service platform + build MDL | write one config.yaml |
| Semantic / metric layer | none formal (example retrieval) | MDL (full-featured, JSON) | one YAML file, git-diffable |
| Infrastructure | vector store | services + vector store + UI | **none** |
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
  question and injected into the prompt; answers cite the metric used.
  Metrics with a `caution` field trigger a **clarifying question** when the
  user's phrasing is ambiguous — and are forbidden from asking when it isn't.
- **Three-layer SQL safety**: a token-level whitelist (single SELECT only,
  CTEs allowed — string literals can't fool it, comments can't smuggle past
  it), connector-enforced timeouts and row caps, and a documented read-only
  account setup as the final backstop. See [SECURITY.md](SECURITY.md).
- **Three dialects out of the box**: MySQL, SQLite (stdlib, Docker-free
  demo), ClickHouse (`pip install queryagent[clickhouse]`). New sources
  implement one 3-method protocol.
- **Two providers, one abstraction**: Anthropic + any OpenAI-compatible
  endpoint (DeepSeek / Qwen / GLM / vLLM / Ollama) via `base_url`. Provider
  tool-call formats never leak into the agent.
- **Event-stream architecture**: the agent yields `AgentEvent`s; the CLI,
  the eval runner, and any future UI are just different consumers. This is
  the load-bearing seam of the codebase.
- **Reproducible evaluation built in**: `queryagent eval` runs a 20-case
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
make eval                                     # self-built 20 cases, demo db
queryagent eval --model deepseek-v4-pro \
  --config examples/demo_ecommerce/config.sqlite.yaml    # strong-model run

queryagent eval --public eval/public/dev-subset.json \
  --db-dir eval/public/databases \
  --config examples/demo_ecommerce/config.sqlite.yaml    # BIRD dev set
```

Methodology: executed row sets compared as order-insensitive multisets with
float tolerance; five metrics including **clarify-behaviour accuracy**
(asked when it should, didn't when it shouldn't). A fixed-seed subset of a
public benchmark serves as an external anchor, with a hard rule that prompts
are never tuned against it ([eval/README.md](eval/README.md)).

### Results (2026-08-20, `deepseek-v4-flash`, temperature 0)

**Self-built suite** (20 cases, ranges over 3 runs — DeepSeek exposes no
sampling seed, so single-run numbers are noise):

| metric | v4-flash (weak) | v4-pro (strong) |
|---|---|---|
| first-execution pass rate | 11–14/18 | **14–15/18** |
| pass rate after self-repair | **17–18/18 (94–100%)** | 16–18/18 |
| clarify-behaviour accuracy | **4/4 (all runs)** | **4/4 (all runs)** |
| cost per case (upper bound) | $0.0007–0.0008 | $0.0019–0.0020 |

The strong model wins at getting it right *first*; after the self-repair
loop the two converge, so the architecture buys a weak model the same final
accuracy at about a third of the cost. Clarify behaviour is identical —
it comes from the prompt protocol, not model strength
([dual-model-analysis.md](eval/results/dual-model-analysis.md)).

**Public benchmark** (BIRD mini-dev, dev/test split — [ADR-004](docs/adr/004-public-subset-external-anchor.md)):

| | dev (100 cases, analysed) | test (200 cases, sealed) |
|---|---|---|
| first-execution pass rate | 39% | 32% |
| pass rate after self-repair | **49%** | **48%** |
| tokens / latency / cost per case | 9,612 / 12.4s / $0.0022 | 8,699 / 11.8s / $0.0019 |

Honest notes, in the order they matter:

- **A previous claim of ours did not survive a bigger sample.** At 30 cases
  per set we measured a dev gain of +14pp against a test gain of +6pp and
  called the gap an overfitting measurement. At 100/200 cases the two sets
  agree within **1pp** — the earlier gap is best explained as noise, which
  is exactly what the power analysis predicted (±25pp for a difference at
  n=30). The samples were expanded *because* of that analysis, and the
  result corrected us.
- **What the numbers can and cannot support.** A before/after comparison on
  the same questions is paired and needs 57–114 cases to detect a real
  effect — 200 covers it. A cross-sample comparison (dev gain vs test gain)
  needs ~1089 per group for 6pp, which is out of reach here; such
  comparisons are reported as directional only.
- **The sealed set stays sealed.** The governing rule is *never change the
  system in response to test results* — not "run it once". It ran once this
  release, on 200 questions freshly sampled from those never used before.
- **Where the remaining failures are** (from dev analysis at the previous
  size, still the operative picture): half were shape rather than substance —
  the right value returned with extra columns — and one general prompt rule
  fixed that class; a quarter are gold-SQL ambiguities that should not be
  fixed; a quarter are genuine capability gaps
  ([dev-failure-analysis.md](eval/results/dev-failure-analysis.md)).
- **Version-over-version numbers are decomposed, not hand-waved.** v0.2.0
  reported 83% first-execution and v0.3.0 reported 61–72%; a controlled
  three-cell run showed the code was a +5pp *improvement* and the entire
  drop came from enabling the model's thinking mode, which lowers
  first-attempt accuracy without lowering final accuracy
  ([version-decomposition.md](eval/results/version-decomposition.md)).
- Costs are peak-rate upper bounds (off-peak is half). Raw reports:
  [eval/results/](eval/results/).

## Architecture

```
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
make test        # ruff + mypy + pytest (153 tests; DB integration tests
                 # auto-skip when demo containers aren't running)
make demo-down   # tear down demo databases
```

## Roadmap

- PostgreSQL connector (validates the Connector seam further)
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
export ANTHROPIC_API_KEY=...    # 或改配置用 DeepSeek 等 OpenAI 兼容端点
queryagent chat --config examples/demo_ecommerce/config.sqlite.yaml
```

安全模型：SQL 白名单（仅单条 SELECT，词法级校验）+ 连接层超时/行数上限 +
只读数据库账号，三层互相独立。评估体系随库附带：`make eval` 一条命令复现
20 条自建用例（含"该问的要问、不该问的不许问"的追问对照组）。
