"""Token accounting and cost estimation for eval reports.

Prices are an **upper-bound estimate**: DeepSeek charges half rate during
off-peak UTC hours, and this module deliberately does not try to work out
which rate applied to a run. Deciding peak vs off-peak per request would
depend on wall-clock time at call time, which makes reported numbers
irreproducible for no analytical gain — so every run is priced at the peak
rate and reported as "at most this much".

Prices captured 2026-08-19 from https://api-docs.deepseek.com/quick_start/pricing
(USD per 1M tokens). They change; unknown models yield ``None`` rather than
a guess, so a stale table never silently invents numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

_PER_MTOK = 1_000_000


@dataclass(frozen=True)
class ModelPricing:
    """Peak-rate USD per 1M tokens, split by cache status."""

    cached_input: float
    input: float
    output: float


PRICING: dict[str, ModelPricing] = {
    "deepseek-v4-flash": ModelPricing(cached_input=0.014, input=0.44, output=1.32),
    "deepseek-v4-pro": ModelPricing(cached_input=0.044, input=1.32, output=3.96),
}

# Aliases the API accepts; responses report the concrete id, but configs and
# CLI overrides may still use the alias.
_ALIASES = {"deepseek-chat": "deepseek-v4-flash"}


@dataclass(frozen=True)
class TokenTotals:
    """Summed usage across one or more model calls."""

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    calls: int = 0

    def __add__(self, other: TokenTotals) -> TokenTotals:
        return TokenTotals(
            input_tokens=self.input_tokens + other.input_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            latency_ms=self.latency_ms + other.latency_ms,
            calls=self.calls + other.calls,
        )

    @property
    def cache_hit_rate(self) -> float:
        """Share of input tokens served from the provider's prompt cache."""
        if self.input_tokens <= 0:
            return 0.0
        return self.cached_input_tokens / self.input_tokens


def price_for_model(model: str) -> ModelPricing | None:
    """Look up pricing, resolving known aliases; None when unpriced."""
    return PRICING.get(_ALIASES.get(model, model))


def estimate_cost_usd(totals: TokenTotals, model: str) -> float | None:
    """Upper-bound cost in USD, or None if the model has no price entry.

    ``cached_input_tokens`` is a subset of ``input_tokens``; the uncached
    remainder is billed at the higher rate.
    """
    pricing = price_for_model(model)
    if pricing is None:
        return None
    uncached = max(totals.input_tokens - totals.cached_input_tokens, 0)
    return (
        uncached * pricing.input
        + totals.cached_input_tokens * pricing.cached_input
        + totals.output_tokens * pricing.output
    ) / _PER_MTOK
