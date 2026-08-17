"""Context assembly: system prompt + schema + matched metrics + history.

Budget model (spec §三 v0.1.1): priority order is
system prompt > tool schemas > matched metrics > table schemas > history.
The first four live in the system prompt and are always kept; when the
estimated total exceeds ``token_budget``, history is trimmed from the oldest
turn, in assistant+tool pairs so tool_use/tool_result blocks never end up
orphaned mid-conversation (provider APIs reject that).

Token estimate is chars//4 — deliberately crude and dependency-free. It
undercounts CJK (closer to one token per char), which makes trimming kick in
*later* than ideal, never earlier; safe direction for a cap.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from queryagent.llm.base import Message
from queryagent.metrics.base import Metric, MetricStore

SYSTEM_PROMPT_TEMPLATE = """\
You are QueryAgent, a careful data analyst working over a {dialect} database.
Current date: {current_date}.

Answer the user's question by inspecting the schema and running read-only SQL.

Rules:
- Write SQL in the {dialect} dialect. Only single SELECT statements (CTEs \
allowed); never attempt to modify data.
- Use the `get_schema` tool if you need column details beyond the schema \
below; use `execute_sql` to run SQL.
- If a query fails, read the database error and fix your SQL before retrying.
- When you have the result, reply with a concise final answer in the same \
language as the question, and include the final SQL you used.

Database schema:
{schema}
"""

_METRICS_HEADER = """
Business metric definitions possibly relevant to this question. Rules:
- Apply a metric's definition and filters ONLY when the question is genuinely
  asking about that metric. NEVER import a metric's filters (e.g. excluding
  test accounts, paid-only) into a question that is not about that metric —
  a plain "how many users" means ALL users unless the question says otherwise.
- When your answer does rely on a metric definition, cite the metric's name
  in the final answer.
"""

_CLARIFY_GUIDANCE = """
IMPORTANT — clarification protocol. A matched metric above carries a Caution
about competing definitions. Before running any SQL, decide:
1. Does the question say which definition to use (e.g. 按注册口径 / 按支付口径)?
   If yes: proceed with that definition, do NOT ask.
2. If no, and the choice between definitions would change the SQL and the
   number: you MUST call the `ask_clarification` tool FIRST — one short
   question naming the options, plus the conflicting metric names. Do not
   guess a definition for an ambiguous reporting question.
3. If the ambiguity does not affect the SQL for this particular question:
   proceed, and state the definition you used.
"""


def estimate_tokens(text: str) -> int:
    """Crude, dependency-free token estimate (see module docstring)."""
    return max(1, len(text) // 4)


class ContextBuilder:
    """Builds the message list handed to ``LLMBackend.complete`` each turn."""

    def __init__(
        self,
        *,
        schema_text: str,
        dialect: str,
        current_date: date | None = None,
        token_budget: int = 32_000,
        metric_store: MetricStore | None = None,
        metrics_top_k: int = 3,
    ) -> None:
        """Bind the builder to one data source (and optionally a metric store).

        Args:
            schema_text: Output of ``render_schema`` for the active source.
            dialect: SQL dialect name, injected into the system prompt.
            current_date: Anchors relative dates ("last month"); defaults to
                today.
            token_budget: Estimated-token cap for one assembled message list.
            metric_store: Optional metric store; when set, metrics matched to
                the question are injected into the system prompt (top_k, not
                all — irrelevant definitions are prompt noise).
            metrics_top_k: How many matched metrics to inject at most.
        """
        self._schema_text = schema_text
        self._dialect = dialect
        self._current_date = current_date or date.today()
        self._token_budget = token_budget
        self._metric_store = metric_store
        self._metrics_top_k = metrics_top_k

    def build(self, question: str, history: Sequence[Message]) -> list[Message]:
        """Assemble the full message list for one model call.

        Args:
            question: The user's natural-language question.
            history: Accumulated assistant/tool messages from earlier turns.

        Returns:
            ``[system, user question, *history]``, history-trimmed to the
            token budget (oldest turns dropped first, in pairs).
        """
        system = SYSTEM_PROMPT_TEMPLATE.format(
            dialect=self._dialect,
            current_date=self._current_date.isoformat(),
            schema=self._schema_text,
        )
        matched = self.match_metrics(question)
        if matched:
            system += _METRICS_HEADER + "".join(_render_metric(m) for m in matched)
            if any(metric.caution for metric in matched):
                system += _CLARIFY_GUIDANCE
        messages = [
            Message(role="system", content=system),
            Message(role="user", content=question),
            *history,
        ]
        return self._trim(messages)

    def match_metrics(self, question: str) -> list[Metric]:
        """Metrics matched to the question (empty without a store)."""
        if self._metric_store is None:
            return []
        return self._metric_store.match(question, top_k=self._metrics_top_k)

    def _trim(self, messages: list[Message]) -> list[Message]:
        """Drop oldest history turns (in pairs) until under the budget."""

        def total() -> int:
            return sum(estimate_tokens(m.content) for m in messages)

        # messages[0] is the system prompt, messages[1] the question; both
        # are always kept — only history (index >= 2) is trimmable.
        while total() > self._token_budget and len(messages) > 2:
            del messages[2]
            if len(messages) > 2 and messages[2].role == "tool":
                del messages[2]  # keep tool results paired with their call
        return messages


def _render_metric(metric: Metric) -> str:
    label = f"{metric.name} ({metric.display_name})" if metric.display_name else metric.name
    lines = [f"\n- {label}: {metric.definition}"]
    if metric.caution:
        lines.append(f"  Caution: {metric.caution}")
    if metric.tables:
        lines.append(f"  Tables: {', '.join(metric.tables)}")
    if metric.sql_hint:
        lines.append(f"  SQL hint: {metric.sql_hint}")
    return "\n".join(lines) + "\n"
