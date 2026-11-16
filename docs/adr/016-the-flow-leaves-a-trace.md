# ADR-016: The confirmed flow leaves a trace, written where decisions are made

Status: accepted · Date: 2026-11-16

## Decision

With `trace: true` (the default, ADR-005) every draft's way to its number is
appended to `<trace_dir>/flows/<draft>-<workspace>.jsonl`, one event per
line: what retrieval returned, which rules the extractor proposed and which
were dropped and why, what the judge said (ADR-015), whether an earlier
choice was offered, each amendment, the confirmation, every refusal with the
step it came from, the admission, and what ran. `queryagent replay <file>`
renders it.

- **Events are produced in the service and the builders, never in a door.**
  The terminal, the page and MCP call the same methods and so leave the same
  trace. A builder, which does not know the draft it builds for, reports
  with `flowtrace.note()`; the service binds the draft around the call.
- **A trace holds only what the acting identity could already see**: the
  question, the rules on that identity's own sheet, citations as references,
  the SQL and its parameters. No document text beyond those rules, no result
  rows. Each event names its workspace.
- **A refused reach into another workspace's draft is filed under the
  caller's own workspace**, and says what the refusal itself says: "not
  permitted".
- **A trace that cannot be written never fails the flow.** One warning on
  stderr; the number is still produced.
- One file per draft is appended to by every process that touches it, each
  line in a single `O_APPEND` write.

## Context

The state file keeps outcomes: the draft, who confirmed which version, what
ran. It did not keep the way there, and three things followed.

- `validate_extraction` produced a `Diagnostic` for every rule it dropped,
  under a docstring saying it "goes to the trace". Nothing received it. A
  maintainer shown 「文档没说清楚」 could not tell silence from a rule that
  failed a check.
- A disputed number could be traced to its SQL and its confirmation, but not
  to what was retrieved, proposed, offered or refused on the way.
- The scenario leak gate has read the trace directory since 1.0.1. Only the
  agent path wrote there, so on the confirmed flow it read an empty folder.

## Consequences

- (+) The dropped-rule diagnostics have a reader.
- (+) The leak gate's trace half is real: the canary scenario now leaves an
  ops trace and a finance trace, and the gate reads zero with both in front
  of it.
- (+) Three processes — an MCP server, a terminal, the server again — write
  one coherent file. An acceptance check drives exactly that.
- (−) Rule text and SQL are on disk in one more place. Same switch, same
  directory and same first-write notice as agent traces.
- **Not an audit log.** It can be switched off, it is pruned (the 200 most
  recently written drafts), and anyone on the machine can edit it. Who
  confirmed what is the state file's to answer.
- **Not traced:** the freshness advisory. It is recomputed every time a
  sheet is shown, by every door, and tracing each showing would bury the
  steps that are decisions.
- The format is not frozen (ADR-014 already excludes trace files).
