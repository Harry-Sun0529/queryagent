# Wayfinder tracker (local markdown)

This repo has no external issue tracker, so wayfinder maps and tickets live
here as files (the skill's local-markdown fallback).

- **Map**: `<effort>-map.md` — the index. Destination, notes, decisions so
  far, fog, out of scope. Never stores ticket detail.
- **Tickets**: `tickets/<NN>-<slug>.md` — one question or task each.
  Front-matter carries `status` (open/closed), `type`
  (research/prototype/grilling/task), `blocked_by`, `claimed_by`.
- **Frontier**: open tickets whose `blocked_by` are all closed and that
  nobody has claimed.

Refer to tickets by **name** (their title), not number, in prose.
