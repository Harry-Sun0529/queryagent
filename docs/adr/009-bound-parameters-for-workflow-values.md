# ADR-009: Bound parameters for workflow values

Status: accepted · Date: 2026-09-10 · Supersedes [ADR-008](008-typed-compilation-before-parameter-binding.md)

## Decision

Values produced by the workflow — today, the dates of a confirmed 统计区间 —
reach the database as parameters, not as text. The compiler emits a
`CompiledQuery(sql, params)` whose statement uses DB-API `?` placeholders.
`Connector.execute` takes `params=()`; each connector adapts `?` to its
driver. The statement text holds only maintainer fragments, identifiers
validated at load time, and placeholders.

## Context

ADR-008 accepted typed compilation for slice 1C and named its own exit: the
moment values other than dates appear. Slice 1C-2 brings grouping now and
leaves value filtering next, and the first literal form ADR-008 chose was
wrong on one dialect — every period lost its first day on SQLite. A literal
is a per-dialect compatibility promise; a parameter hands that promise to
the driver, which is where it belongs.

The drivers differ. `sqlite3` binds at the engine. PyMySQL and
clickhouse-driver escape client-side and substitute with `query % escaped`,
so their placeholders are `%s` / `%(name)s` and every other `%` in the
statement must be doubled. The connectors do that by tokenising with
sqlparse — a `?` or `%` inside a string literal stays literal — rather than
asking maintainers to remember that `LIKE 'a%'` means something different
once a value is bound.

## Consequences

- (+) No workflow value passes through this project's string building. The
  compiled text is checked by the safety layer exactly as it is sent.
- (+) Runs record the statement and its values separately, and the CLI
  shows both, so an audit reads what the driver received.
- (+) The same mechanism carries the next kind of value (a user-chosen
  channel, a status list) without another ADR.
- (−) "Bound" means different things per driver. On MySQL and ClickHouse it
  is the driver's escaper, not a server-side prepared statement. That is the
  DB-API contract and it removes our own concatenation; it is not a stronger
  guarantee than the driver's escaping, and the docs say so.
- (−) Values are bound as ISO strings. That keeps sqlite3's deprecated
  default date adapter out of the path and renders the same text the typed
  compiler did, so the three dialects compare exactly as before — verified
  against each one's native month function.
- (−) Calls without `params` send the statement untouched (the agent's own
  SQL takes that path), so `%` handling differs by whether values were
  supplied. That is deliberate: rewriting statements nobody bound would
  change behaviour that works today.
