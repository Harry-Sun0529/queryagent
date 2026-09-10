# ADR-008: Typed compilation before parameter binding

Status: accepted · Date: 2026-09-10

## Decision

A confirmed 统计区间 reaches SQL through a typed compiler, not through bound
parameters. Two kinds of value may appear in a compiled statement:
maintainer-authored fragments from `query_mappings.yaml` (`measure`,
`where`), and dates that exist only as `datetime.date` objects decoded from a
rule of the strict form `YYYY-MM-DD..YYYY-MM-DD`. Nothing a user typed and
nothing a document said is interpolated. The `Connector` protocol is
unchanged.

## Context

Slice 1C needs a date condition in the query. The principled mechanism is
parameter binding, but `Connector.execute` takes a SQL string, and binding
would mean extending the protocol and adapting three dialects whose
placeholder styles differ (`?`, `%s`, `%(name)s`), plus the agent's
`execute_sql` tool path. The handoff (§11.3) allows the first slice to use a
strictly controlled typed compiler instead, provided no unvalidated user
value is concatenated.

## Consequences

- (+) The only new value that enters SQL is a date the parser produced; the
  injection surface does not grow. Tests try a forged period, a quoted
  variant key and SQL written into user and document rules; none reaches the
  output.
- (+) No dialect-specific binding code; the same bounds run on SQLite, MySQL
  and ClickHouse, each checked against its own native month function.
- (−) Maintainer fragments are concatenated as written. That is the trust
  the whole-statement `sql:` mappings already had, not a new surface, but it
  means a mapping change must be reviewed like code.
- (−) Literal forms are a compatibility promise per dialect. The first form
  chosen (`'YYYY-MM-DD 00:00:00'`) was wrong: SQLite sorts date-only text
  below it and dropped each period's first day. Bounds are bare dates now; any
  new value type will need the same per-dialect verification.
- (−) Anything beyond dates — a user-chosen region, a status list — needs
  binding, and that is the point at which this ADR should be superseded.
