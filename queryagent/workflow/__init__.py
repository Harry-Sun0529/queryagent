"""The trusted workflow layer: state, provenance, confirmation, execution.

Slice 1A (docs/specs/workflow-slice-1a-2026-09.md) establishes the boundary
that the existing agent loop does not have: a business query executes only
against a server-side confirmation record bound to the exact semantics the
user saw. The model participates by proposing; it never authorises.
"""

from __future__ import annotations
