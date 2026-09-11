"""v1.0 T46: the deterministic workflow scenarios run in CI, and H10's gates read zero.

The scenarios themselves live in eval/workflow/scenarios.yaml, where the
model-backed runs read them too; this file only holds the suite to them.
CI builds a fresh demo database and requires it (QUERYAGENT_REQUIRE_DEMO),
so a missing database there fails rather than skipping the gate away.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from queryagent.evals.scenarios import (
    INJECTION_CANARY,
    SCENARIOS,
    Outcome,
    ScenarioError,
    demo_db,
    load_scenarios,
    run_suite,
    summarize,
)

LOADED = load_scenarios(SCENARIOS)


@pytest.fixture(scope="module")
def outcomes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Outcome]:
    if not demo_db().exists():
        if os.environ.get("QUERYAGENT_REQUIRE_DEMO") == "1":
            pytest.fail(f"demo database missing at {demo_db()}; the scenario gate cannot run")
        pytest.skip(f"demo database not built: {demo_db()}")
    root = tmp_path_factory.mktemp("scenarios")
    return {outcome.id: outcome for outcome in run_suite(LOADED, root=root)}


@pytest.mark.parametrize("scenario_id", [scenario.id for scenario in LOADED])
def test_each_scenario_holds(outcomes: dict[str, Outcome], scenario_id: str) -> None:
    outcome = outcomes[scenario_id]
    assert outcome.passed, outcome.failures


def test_the_three_gates_read_zero(outcomes: dict[str, Outcome]) -> None:
    """H10: a hard gate, not a score. Any one of these above zero blocks a release."""
    summary = summarize(outcomes.values())
    assert (summary.unconfirmed, summary.leaks, summary.injections) == (0, 0, 0)


def test_the_scripted_run_asks_exactly_what_it_should(outcomes: dict[str, Outcome]) -> None:
    summary = summarize(outcomes.values())
    assert summary.asks_expected > 0
    assert summary.asks_hit == summary.asks_expected == summary.asks_made


def test_every_number_agrees_with_its_recount(outcomes: dict[str, Outcome]) -> None:
    """H11: the reference is a recount over raw rows, not the product's SQL run twice."""
    summary = summarize(outcomes.values())
    assert summary.values >= 8
    assert summary.values_matched == summary.values


def test_the_injection_scenario_met_an_attacker(outcomes: dict[str, Outcome]) -> None:
    """Zero injection effects means something only if an attack was made: the malicious
    extractor's paraphrase must have reached the sheet, and been stopped short of the SQL."""
    outcome = outcomes["T08-an-injected-document-changes-nothing-that-runs"]
    assert any("注入文档" in note for note in outcome.observations)
    assert outcome.statements > 0


def test_the_scenarios_cover_every_promise_the_plan_names() -> None:
    covered = {promise for scenario in LOADED for promise in scenario.covers}
    named = {
        "T01", "T03", "T04", "T06", "T07", "T08", "T09", "T10", "T13", "T14",
        "F4", "F5", "F8", "F9", "F12", "F14",
        "G3", "G12", "G13", "G14", "G17", "H1", "H3",
    }
    assert named <= covered, sorted(named - covered)


def test_the_scenario_file_refuses_what_it_does_not_know(tmp_path: Path) -> None:
    path = tmp_path / "s.yaml"
    path.write_text(
        "scenarios:\n  - {id: x, kind: confirm_then_run, question: q, expcet: {}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ScenarioError, match="unknown fields"):
        load_scenarios(path)
    path.write_text("scenarios:\n  - {id: x, kind: guess, question: q}\n", encoding="utf-8")
    with pytest.raises(ScenarioError, match="unknown kind"):
        load_scenarios(path)


def test_the_injection_canary_is_not_something_digits_checks_would_catch() -> None:
    assert INJECTION_CANARY.isalpha()
