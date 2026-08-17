# Security Model

QueryAgent turns natural language into SQL and executes it. The security
design assumes **the model's output is untrusted input** — the same stance
you would take toward user-supplied SQL.

## Threat model

1. **Destructive SQL** — from model error, or from prompt injection: schema
   comments, table contents and database error messages all flow back into
   the prompt, and any of them can carry adversarial instructions
   ("ignore previous instructions and DROP …").
2. **Data modification via smuggling** — multi-statement payloads
   (`SELECT 1; DROP TABLE users`), comment tricks, CTE wrappers.
3. **Resource exhaustion** — runaway queries (cartesian joins, unbounded
   recursion) starving the database.

## Defence in depth (three independent layers)

| layer | mechanism | trusts |
|---|---|---|
| 1. SQL whitelist (`safety.py`) | single SELECT only (CTE allowed); DML/DDL, multi-statement and comment-smuggling rejected by token-level parsing, not regex | nothing the model says |
| 2. Connector limits | per-query timeout + row cap enforced in the driver layer (`MAX_EXECUTION_TIME` on MySQL, progress-handler deadline on SQLite) | not the SQL that passed layer 1 |
| 3. Read-only account | documented setup: the agent's DB credentials have `SELECT` grants only | not this codebase |

Layer 3 is the backstop: even if a parser bug lets a write statement through
layers 1–2, the database refuses it. This is why the README insists on a
read-only account rather than treating it as optional hardening.

## Prompt injection: honest boundary

The whitelist cannot stop an injected prompt from making the agent run a
*wrong but valid* SELECT (e.g. exfiltrating more columns than the question
needed, within the row cap). Mitigations are scope limits, not guarantees:
row caps bound volume, the event stream makes every executed SQL visible and
auditable, and deployments should grant the read-only account access only to
tables the agent legitimately needs.

## Key handling

API keys are read exclusively from environment variables
(`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`); the config loader actively rejects
credential-looking keys in `config.yaml`. Demo database credentials are
throwaway local defaults that exist only in `docker-compose.yml`.

## Reporting

Open a GitHub issue for non-sensitive reports. For anything sensitive,
contact the maintainer directly (see repo profile) before public disclosure.
