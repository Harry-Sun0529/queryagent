"""Context assembly: system prompt + schema + history.

Ownership: AI-ASSISTED-R (spec §〇) — first draft awaiting the human's
substantive refactor; ``# REVIEW-ME`` markers flag the decision points.

v0.1.0 deliberately ships the naive version: system prompt + full schema +
history, concatenated with no trimming. The token-budget skeleton below is
the reserved seam that v0.1.1 fills with the actual trimming logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from queryagent.llm.base import Message

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
# REVIEW-ME: the full schema is embedded in the system prompt. Alternative:
# rely solely on the get_schema tool (cheaper first call, but adds one round
# trip to nearly every question). Demo-scale schemas are small, so injection
# wins for now; the v0.1.1 budget logic revisits this for wide databases.


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used by the (future) budget allocator.

    # REVIEW-ME: chars//4 is tuned for English; CJK-heavy text runs closer to
    # one token per character. Alternatives: weight by unicode range, or use a
    # real tokenizer (rejected for now: zero-dependency constraint, spec §四).
    """
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
    ) -> None:
        """Bind the builder to one data source.

        Args:
            schema_text: Output of ``render_schema`` for the active source.
            dialect: SQL dialect name, injected into the system prompt.
            current_date: Anchors relative dates ("last month"); defaults to
                today.
            token_budget: Total context budget; unused until v0.1.1 trimming.
        """
        self._schema_text = schema_text
        self._dialect = dialect
        self._current_date = current_date or date.today()
        self._token_budget = token_budget

    def build(self, question: str, history: Sequence[Message]) -> list[Message]:
        """Assemble the full message list for one model call.

        Args:
            question: The user's natural-language question.
            history: Accumulated assistant/tool messages from earlier turns.

        Returns:
            ``[system, user question, *history]`` — untrimmed in v0.1.0.
        """
        system = SYSTEM_PROMPT_TEMPLATE.format(
            dialect=self._dialect,
            current_date=self._current_date.isoformat(),
            schema=self._schema_text,
        )
        return [
            Message(role="system", content=system),
            Message(role="user", content=question),
            *history,
        ]

    def _allocate_budget(self) -> dict[str, int]:
        """Reserved seam: v0.1.1 fills this with real budget allocation.

        Priority order (spec §三 v0.1.1): system prompt > tool schemas >
        matched metrics > question-relevant table schemas > other tables >
        history. When over budget, trim from the tail of that list.

        # REVIEW-ME: trimming history from the oldest turn is the planned
        # default; the alternative is summarising old turns instead of
        # dropping them (better recall, more complexity + one extra LLM call).
        """
        raise NotImplementedError("v0.1.1: token budget allocation (spec §三)")
