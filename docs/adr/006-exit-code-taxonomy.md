# ADR-006: Three exit codes, because failures are not all alike

Status: accepted · Date: 2026-08-19

## Decision

The CLI classifies every failure into one of three exit codes:

| code | meaning | examples |
|---|---|---|
| 2 | the user's environment or input | missing/invalid API key, malformed config, missing database or optional driver |
| 70 (`EX_SOFTWARE`) | a defect in QueryAgent | any unexpected exception |
| 75 (`EX_TEMPFAIL`) | upstream trouble, retryable | HTTP 429/5xx after retries, connection refused, timeouts |

## Context

Every failure used to exit 2, which told a human "you probably
misconfigured something" and told a script nothing at all. Those are three
different situations with three different correct reactions: fix your
setup, report a bug, or wait and retry. Collapsing them makes batch eval
runs impossible to automate (a rate limit and a wrong key look identical)
and sends users hunting for configuration mistakes that do not exist.

A rejected key (401) is deliberately a user error rather than a temporary
failure: it will not start working on its own, and retrying it is waste.

## Consequences

- (+) `queryagent eval` in a loop can retry on 75 and stop on 2.
- (+) A bug reports itself as a bug and asks for `--verbose`, instead of
  blaming the user's config.
- (−) The classification is heuristic (it inspects exception types and
  message text); a novel upstream error may land in 70 until taught.
