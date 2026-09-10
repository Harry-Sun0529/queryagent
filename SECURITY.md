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
joins and aggregations can still be costly before producing a row. Human
confirmation now exists (`queryagent flow`); per-source total budgets and
admission control still do not.

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
table should already consider readable.

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
