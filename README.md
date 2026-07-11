# QueryAgent

Zero-infrastructure Text-to-SQL agent for small data teams and individual data
engineers: `pip install`, point it at your database, ask questions in natural
language. Business metric definitions live in one YAML file that goes into
git — reviewing a metric change is just reviewing a PR.

> **Status**: v0.1.0 under construction. Not released — interfaces may still move.

## Why another Text-to-SQL tool?

On the complexity spectrum *Vanna (train a RAG model first) → WrenAI (deploy a
multi-service platform) → DB-GPT (orchestrate multiple agents)*, QueryAgent
takes the leftmost position: **no vector store, no services, no UI, no agent
framework**. One process, one `config.yaml`, one `metrics.yaml`. If you are a
3-person data team or a single engineer who wants metric definitions to take
effect in five minutes, everything else is too heavy — that lightness is the
feature.

## Architecture (v0.1.0)

```
question ──▶ ReAct loop (agent.py) ──▶ AgentEvent stream ──▶ consumers
                 │                                            (demo printer,
                 ├─ LLMBackend        (llm/)                   v0.1.1 CLI,
                 ├─ ToolRegistry      (tools.py)               v0.2.0 eval)
                 │    ├─ get_schema
                 │    └─ execute_sql ─▶ safety.py ─▶ Connector (connectors/)
                 └─ ContextBuilder    (context.py)
```

The event stream is the load-bearing interface: the agent never prints or
renders; every front end is just a different consumer of the same
`Iterator[AgentEvent]`.

- `agent.py` — hand-written ReAct loop: four explicit termination conditions,
  parse-failure fallback. No framework.
- `safety.py` — SQL whitelist (single SELECT only), backed by connector-level
  timeouts/row caps and a read-only DB account. Three independent layers.
- `llm/` — provider abstraction; tool-call format differences are absorbed
  per backend, the agent never sees raw SDK responses.
- `connectors/` — data source abstraction (`dialect` drives SQL generation).
- `context.py` — context assembly; token budgeting lands in v0.1.1.

## Quickstart (dev preview — MySQL via Docker)

```bash
pip install -e ".[dev]"
make demo-up                 # generates demo data, starts MySQL on :3307
export ANTHROPIC_API_KEY=sk-ant-...
python -m queryagent.demo "上个月每天的新增用户数"
```

The demo database is a fictional e-commerce shop (~50k users, ~200k orders
over the last 6 months). For your own database, create a **read-only**
account and point `config.yaml` at it:

```sql
CREATE USER 'queryagent_ro'@'%' IDENTIFIED BY '...';
GRANT SELECT ON your_db.* TO 'queryagent_ro'@'%';
```

## Development

```bash
make test        # ruff + mypy + pytest; red means don't commit
```

This repo follows a strict human/AI code-ownership protocol: `agent.py` and
the `safety.py` rule design are human-written; reviewable AI-drafted modules
carry `# REVIEW-ME:` markers at real decision points and require a human
refactor commit before they count as merged. See `prompt-log.md` for the
collaboration record.

## License

MIT
