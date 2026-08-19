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
  flow is one readable generator with four explicit termination conditions,
  parse-failure fallback, and a self-repair loop (database errors are fed
  back to the model, capped at 3 retries).
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
make eval                        # self-built 20 cases against the demo db
queryagent eval --backend openai_compatible --model deepseek-chat \
  --base-url https://api.deepseek.com \
  --config examples/demo_ecommerce/config.sqlite.yaml   # dual-model comparison
```

Methodology: executed row sets compared as order-insensitive multisets with
float tolerance; five metrics including **clarify-behaviour accuracy**
(asked when it should, didn't when it shouldn't). A fixed-seed subset of a
public benchmark serves as an external anchor, with a hard rule that prompts
are never tuned against it ([eval/README.md](eval/README.md)).

### Results (`deepseek-chat`, temperature 0, 2026-08-17)

| metric | self-built (20 cases) | BIRD mini-dev subset (30 cases, seed 42) |
|---|---|---|
| first-execution pass rate | 15/18 (83%) | 10/30 (33%) |
| pass rate after self-repair | **18/18 (100%)** | 14/30 (47%) |
| metric hit rate | 3/4 | n/a |
| clarify-behaviour accuracy | **4/4** | n/a |
| average tool calls | 1.35 | 2.83 |

Honest notes, in the order they matter:

- **The self-built set was iterated on — that is its job.** The first run
  scored 50%; failure analysis exposed a metric-matching noise bug (one
  shared bigram dragged a metric's filters into unrelated questions), an
  unstable clarify trigger at provider-default temperature, and two brittle
  case designs (rolling-date conventions). All fixed, all in git history.
- **The public subset ran exactly once, zero tuning** — it exists to keep
  the self-built numbers honest. 47% after self-repair for a small general
  model with a generic zero-shot agent is the unvarnished anchor; the gap
  vs the self-built set is mostly schema unfamiliarity (avg tool calls
  2.83 vs 1.35 — the agent explores before it answers).
- One public case failed because the *gold* SQL exceeded the harness's 30s
  timeout; counted as a failure anyway (conservative).
- Self-built denominators: 18 result-checked cases; the 2 ask-clarify cases
  score behaviour, not result sets.
- A strong-model column (Claude) will be added when run; raw reports live
  in [eval/results/](eval/results/).

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
