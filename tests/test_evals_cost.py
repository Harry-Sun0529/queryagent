"""Unit tests for token pricing and cost estimation."""

from __future__ import annotations

import pytest

from queryagent.evals.cost import TokenTotals, estimate_cost_usd, price_for_model


def test_known_model_prices_cached_input_separately() -> None:
    # 1M cache-miss input + 1M cached input + 1M output on v4-flash (peak):
    # 0.44 + 0.014 + 1.32
    totals = TokenTotals(
        input_tokens=2_000_000, cached_input_tokens=1_000_000, output_tokens=1_000_000
    )
    cost = estimate_cost_usd(totals, "deepseek-v4-flash")
    assert cost is not None
    assert cost == pytest.approx(0.44 + 0.014 + 1.32, rel=1e-6)


def test_pro_is_more_expensive_than_flash() -> None:
    totals = TokenTotals(input_tokens=100_000, cached_input_tokens=0, output_tokens=10_000)
    flash = estimate_cost_usd(totals, "deepseek-v4-flash")
    pro = estimate_cost_usd(totals, "deepseek-v4-pro")
    assert flash is not None and pro is not None
    assert pro > flash


def test_unknown_model_returns_none_rather_than_guessing() -> None:
    totals = TokenTotals(input_tokens=1000, cached_input_tokens=0, output_tokens=100)
    assert estimate_cost_usd(totals, "some-other-model") is None
    assert estimate_cost_usd(totals, "") is None


def test_model_alias_resolves_to_pricing() -> None:
    # deepseek-chat is an alias the API accepts; responses report the real id,
    # but a config may still name the alias.
    assert price_for_model("deepseek-chat") is not None


def test_zero_usage_costs_nothing() -> None:
    assert estimate_cost_usd(TokenTotals(), "deepseek-v4-flash") == 0.0


def test_totals_add() -> None:
    a = TokenTotals(input_tokens=10, cached_input_tokens=4, output_tokens=2, latency_ms=100)
    b = TokenTotals(input_tokens=5, cached_input_tokens=1, output_tokens=3, latency_ms=50)
    total = a + b
    assert total.input_tokens == 15
    assert total.cached_input_tokens == 5
    assert total.output_tokens == 5
    assert total.latency_ms == 150


def test_cache_hit_rate() -> None:
    assert TokenTotals(input_tokens=100, cached_input_tokens=80).cache_hit_rate == 0.8
    assert TokenTotals().cache_hit_rate == 0.0
