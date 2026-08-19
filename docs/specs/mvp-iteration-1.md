# MVP Iteration 1 — spec

> Process note: development follows the mattpocock skills (implement → tdd on
> pre-agreed seams → code-review two-axis). This file is the Spec axis source.
> Constraint: DeepSeek (`deepseek-chat`) is the only live model available;
> all defaults and live verification target it.

## Goal

Close the gap between "works end to end" and "someone can actually use this
daily": DeepSeek-first out of the box, follow-up questions in chat, a
scriptable one-shot command, and a backend that survives transient API
failures.

## Tickets

### T1 — DeepSeek-first defaults

All three example configs default to `openai_compatible` + `deepseek-chat`
(+ `base_url`), with the Anthropic block commented. README quickstart leads
with `OPENAI_API_KEY` (DeepSeek). Rationale: the maintainer has no Anthropic
key; a default config that cannot run is a broken quickstart.

### T2 — Multi-turn conversation in chat

Follow-up questions must see earlier turns ("那按渠道拆分呢？" after a
new-users question must know the metric and month under discussion).

- Seam: `run_agent(..., conversation: Sequence[Message] = ())` — finished
  prior turns as plain user/assistant text messages (no tool blocks:
  cheaper, and old tool output is stale context).
- Seam: `ContextBuilder.build(question, history, *, conversation=())` →
  message order `[system, *conversation, user question, *current-run history]`.
- Budget: conversation is trimmed **before** current-run history (oldest
  first, in user+assistant pairs) — the current run's tool exchanges are
  worth more than old chat.
- CLI chat keeps the conversation; a clarify round stores the augmented
  question (it carries the user's disambiguation, which follow-ups need).
- Eval runner passes no conversation — cases stay independent.

### T3 — `queryagent ask` (one-shot)

`queryagent ask "问题" --config ... [--verbose] [--max-turns N]` runs one
question and exits: answer → exit 0; terminal ErrorEvent → exit 2; a
ClarifyEvent prints the clarifying question and exits 0 (in one-shot mode
the question *is* the output). Thin adapter over the chat wiring — no new
logic beyond exit codes.

### T4 — Transient-failure retry in OpenAICompatibleBackend

Retry `complete()` on httpx transport errors, HTTP 429 and HTTP 5xx: up to
2 retries with linear backoff (injectable for tests). Non-429 4xx fails
immediately (a bad key does not get better by retrying). After exhaustion,
surface the last error unchanged in shape (RuntimeError / transport error).

### T5 — Decision records + agent context

`docs/adr/` with the four standing decisions (no agent framework; metrics
as YAML in git, not a vector store; eval compares executed results, not SQL
text; public-subset external anchor with no-tuning rule). `CONTEXT.md` at
the repo root: domain language (metric/口径, clarify, seam map of the
codebase) for humans and agents.

## Pre-agreed test seams (tdd skill)

1. `ContextBuilder.build` — conversation ordering + trim priority.
2. `run_agent` — conversation is forwarded to the backend; behaviour with
   conversation present is otherwise unchanged.
3. `OpenAICompatibleBackend.complete` — retry matrix via MockTransport
   (500→200 recovers; transport-error→200 recovers; persistent 500 fails
   after 3 attempts; 401 fails on the first attempt).

CLI (`ask`, chat conversation folding) is adapter wiring — covered by a live
DeepSeek smoke run instead of unit tests, same as `chat` today.

## Acceptance

- `make test` green; new seams covered.
- Live (DeepSeek): `queryagent ask` answers on the demo db; a chat session
  answers a follow-up that only makes sense with memory of turn 1.
- Self-built eval re-run: no regression vs 15/18 · 18/18 · 4/4 (same-day
  baseline; single-question prompts are unchanged by T2, so parity expected).
- Version 0.2.0, CHANGELOG updated, pushed.
