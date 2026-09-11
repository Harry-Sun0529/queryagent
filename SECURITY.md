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
4. **Indexed documents** — when a knowledge base is configured, company
   handbooks flow into the prompt too. This is the *easiest* of the four for
   an insider to write to: anyone who can edit a Markdown file in an indexed
   directory can put "ignore previous instructions" in front of the model.
5. **The calling agent** — since 1.0 an agent host can drive the confirmed
   flow over MCP. The agent may be wrong, or steered by something it read;
   the one thing it must not be able to do is approve a query on its
   person's behalf. The confirmation page it points the person to is a local
   web server, with the usual local-server attacks against it.

## Defence in depth (three independent layers)

| layer | mechanism | trusts |
|---|---|---|
| 1. SQL whitelist (`safety.py`) | single SELECT only (CTE allowed); DML/DDL, multi-statement and comment-smuggling rejected by token-level parsing, not regex | nothing the model says |
| 2. Connector limits | per-query timeout + row cap enforced in the driver layer (`MAX_EXECUTION_TIME` on MySQL, progress-handler deadline on SQLite) | not the SQL that passed layer 1 |
| 3. Read-only account | documented setup: the agent's DB credentials have `SELECT` grants only | not this codebase |
| 4. Evidence isolation (`knowledge/`) | retrieval is scoped by workspace in the query itself; extraction runs with no tools; the model cites by index into an authorised menu and never emits a document identifier | nothing a document says |

Layer 3 is the backstop: even if a parser bug lets a write statement through
layers 1–2, the database refuses it. This is why the README insists on a
read-only account rather than treating it as optional hardening.

## Execution limits and their boundaries

MySQL refuses to execute a query if setting its server execution timeout
fails. Client read/write timeouts (30 seconds by default) and bounded pool
waits cover stalled connections separately; a client timeout is not proof
that the server query was cancelled. SELECT results stream at most the row
cap plus one row to detect truncation. A truncated connection is discarded
rather than draining its remaining rows into memory.

A row cap is **not a scan, CPU or memory budget on the server**. Expensive
joins and aggregations can still be costly before producing a row. Since
v0.9 a maintainer can set totals in `budget:`
([ADR-011](docs/adr/011-budgets-are-configuration.md)): statements per
request, statements and client-measured seconds per subject per day,
requests executing at once, and — on ClickHouse only — the rows one
statement may read, enforced by the engine. A request is admitted before its
first statement or refused with nothing run. MySQL and SQLite have no scan
limit; the per-statement timeout is the only bound there, and configuring
one is refused at load rather than silently ignored. A per-subject allowance
is only as strong as the identity it is keyed on: locally, `flow --subject`
is the trusted user's own choice, so per-person allowances need an identity
supplied by a host.

## Prompt injection: honest boundary

The whitelist cannot stop an injected prompt from making the agent run a
*wrong but valid* SELECT (e.g. exfiltrating more columns than the question
needed, within the row cap). Mitigations are scope limits, not guarantees:
row caps bound volume, the event stream makes every executed SQL visible and
auditable, and deployments should grant the read-only account access only to
tables the agent legitimately needs.

## Compiled queries (`queryagent flow`)

A confirmed 统计区间 reaches the database as bound parameters
([ADR-009](docs/adr/009-bound-parameters-for-workflow-values.md), superseding
the typed compilation of ADR-008). The statement text is assembled from
maintainer fragments in `query_mappings.yaml`, identifiers validated when
that file loads, and `?` placeholders; the dates travel beside it, each
decoded from a rule of the form `YYYY-MM-DD..YYYY-MM-DD` first. The
question's text, document rules and the user's own conventions are never
part of the statement. Mapping fragments are concatenated as written — the
trust whole-statement mappings always had — so a mapping change is a code
change and should be reviewed as one. The statement, with its placeholders,
passes the layer-1 whitelist before it runs.

What "bound" means depends on the driver: SQLite binds at the engine;
PyMySQL and clickhouse-driver escape each value client-side and substitute
it. That removes this project's own string building from the path; it is not
a server-side prepared statement, and no stronger than the driver's escaper.

Each confirmed run of a structured mapping executes a second statement,
`SELECT MAX(time_column) FROM table`, generated from the same validated
identifiers, through the same whitelist and executor, and only after the
confirmation holds. It discloses one fact to whoever runs the query — the
date of the newest record in that table — which a deployment granting the
table should already consider readable. With
`workflow.freshness_before_confirm: probe` (off by default,
[ADR-010](docs/adr/010-freshness-before-confirmation.md)) the same statement
may also run *before* confirmation, to warn on the sheet. It is the only
statement that can; it runs with its own short timeout, is charged to the
budget, and is cached per table — not per subject, since the answer is the
same for everyone who may query the table.

A value filter (「广告渠道」) is bound like the dates, and only a value a
maintainer declared under `values:` can become one; anything else is asked
about, so a question cannot choose what is compared.

## Remembered choices

历史选择 reads only the acting subject's own confirmed, successful runs in
the same workspace; nothing one subject chose is offered to another. Those
drafts are business data at rest in the workflow state file, like every
other draft — deleting the file forgets them. A remembered choice that
adopted a document is re-checked against the subject's current access
before it is offered, and one that no longer checks out is dropped without
saying which document it was.

## Agents over MCP (`queryagent mcp`)

[ADR-013](docs/adr/013-agents-prepare-people-confirm.md). The MCP server has
five tools — list, prepare, amend, status, execute — and none of them
confirms. Beneath that, the service refuses a confirmation from the MCP
channel, and the lookup `execute_query` relies on accepts only confirmations
recorded from the terminal or the page. Without one, nothing runs.

- **Identity** is the `--subject` / `--workspace` the host's configuration
  starts the server with. No tool takes an identity; an argument naming one
  is refused.
- **What the agent fills in** is marked 「Agent 代填」, is part of the content
  hash, is highlighted on the page, and is named again on the result. It
  cannot be written as 「本次约定」 or 「文档依据」.
- **One confirmation authorises one run.** The confirmation is the
  idempotency key; running again takes a person confirming again.
- stdout carries protocol frames only.

## The confirmation page (`queryagent web`)

Bound to 127.0.0.1, with no option to bind anywhere else. Logging in takes a
link printed on the terminal that started the server; it works once, and
anyone who can read that terminal can use it. The session lives in the
server's memory, as an `HttpOnly; SameSite=Strict` cookie, so a restart logs
everyone out.

| attack | check, in this order |
|---|---|
| DNS rebinding (another site's hostname resolving to 127.0.0.1) | every request's `Host` must be this server's own address |
| CSRF (another site's form, riding the cookie) | `SameSite=Strict`; every POST's `Origin` must be this server; every form carries an HMAC token bound to the session, the action, and the draft version and hash on screen |
| XSS (documents and questions are untrusted text) | every string is HTML-escaped; `Content-Security-Policy: default-src 'none'` runs no script at all; `frame-ancestors 'none'` |

A refused request changes nothing. A confirmation names the version and hash
it was rendered with, so a draft an agent amends while the person reads is
refused rather than confirmed in its new form. The login token is masked in
the request log.

**Honest boundary.** This design stops an agent confirming *through the tool
protocol*, and another website confirming *through the browser*. It does not
stop an agent that has an arbitrary shell as the same OS user: that agent can
run `queryagent confirm`, read the login link off the terminal, or write the
state file directly. There is no TLS, which is acceptable only because
nothing leaves the loopback interface. Deployments with several people need
real authentication, which 1.0 does not provide.

## Indexed documents

Document import is the only filesystem read path in this codebase, and it
reads whatever it finds under a configured source. `knowledge.root` confines
every source and both sides are resolved, so a symlink inside the root
cannot point out of it — without that, a mis-set source could pull `.env` or
a credentials file into a model prompt.

What the code guarantees, and what it does not:

- **Guaranteed**: a rule marked 「文档依据」 cites a chunk that exists, that
  this subject was authorised for, and that verbatim contains the quoted
  text. The model selects by index into a menu the server built, so it
  cannot name a document it was not shown. Extraction is called with no
  tools. Executable SQL still comes only from a maintainer mapping. A
  document can *choose* which mapping runs — when its verified quote
  contains the words a mapping declares under `enforces:`, and the documents
  agree — but the choice is shown as 「文档依据」 with its citation and still
  needs the user's confirmation, and the text itself never enters a query.
- **Not guaranteed**: that the quoted text *supports* the rule stated. Whole
  entailment is a model judgement, not a boundary. Numbers in the rule must
  appear in the quote and unrelated citations are filtered by n-gram
  overlap, but neither detects a rule that quotes a qualifying clause and
  drops the sentence it qualified. The quote and its location are shown on
  the confirmation sheet because the final judgement is the reader's. The
  same holds for correspondence: 「已由所选口径执行」 means the quote
  contains words the maintainer declared for that reading, not that its
  meaning was verified. A maintainer who declares broad words (「日期」)
  makes unrelated sentences correspond; the words are reviewed with the
  mapping file, and a quote containing two readings' words claims neither.

Semantic retrieval, when enabled, sends document text to the configured
embeddings endpoint. It is off unless configured.

## Traces on disk

By default every `chat` / `ask` run writes its full event stream — question,
SQL, observations (including result rows) and token usage — to
`.queryagent/traces/*.jsonl`. Against a real database that is business data
at rest on the local filesystem. With a knowledge base configured, document
excerpts are part of that too.

Mitigations: a stderr notice on the first write, `--no-trace` and config
`trace: false`, a 50-file retention cap, and `.queryagent/` in `.gitignore`
so traces cannot be committed by accident. Reasoning for the default —
including why partial redaction was rejected — is in
[ADR-005](docs/adr/005-traces-on-by-default.md). On sensitive data, set
`trace: false`.

## Key handling

API keys are read exclusively from environment variables
(`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `QUERYAGENT_EMBEDDING_API_KEY`);
the config loader actively rejects credential-looking keys in every section
of `config.yaml`, not only the LLM one. Demo database credentials are
throwaway local defaults that exist only in `docker-compose.yml`.

## Reporting

Open a GitHub issue for non-sensitive reports. For anything sensitive,
contact the maintainer directly (see repo profile) before public disclosure.
