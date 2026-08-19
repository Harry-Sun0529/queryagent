# ADR-003: Eval compares executed results, not SQL text

Status: accepted · Date: 2026-08-19

## Decision

A case passes when some successfully executed agent SQL reproduces the
reference SQL's row set — compared as an order-insensitive multiset with
float tolerance (4-decimal rounding). SQL text is never compared.

## Context

Equivalent SQL is syntactically unbounded (aliases, CTE vs subquery, join
order). Text similarity misgrades both directions. Executed row sets are the
only equivalence oracle that doesn't require a SQL theorem prover.

## Consequences

- (+) Robust to the model's stylistic choices; robust to driver type
  differences (Decimal vs float vs ISO strings) via normalisation.
- (−) Requires executing the reference SQL (it passes the same safety gate),
  and "accidentally equal" results are theoretically possible — mitigated by
  specific expected values.
- Rounding as tolerance keeps rows hashable for multiset counting; pairwise
  isclose was rejected as O(n²) with no practical gain under row caps.
