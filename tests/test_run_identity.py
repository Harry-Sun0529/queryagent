"""Resume must identify the experiment, not a coincidentally matching filename."""

from dataclasses import replace
from pathlib import Path

from queryagent.config import AppConfig, DatabaseConfig, LLMConfig, SafetyConfig
from queryagent.evals.identity import run_signature


def test_resume_identity_tracks_effective_inputs(tmp_path: Path) -> None:
    cases = tmp_path / "cases.yaml"
    cases.write_text("cases: []")
    db = tmp_path / "data.sqlite"
    db.write_bytes(b"snapshot one")
    metrics = tmp_path / "metrics.yaml"
    metrics.write_text("metrics: []")
    config = AppConfig(
        LLMConfig("openai_compatible", "m", "https://example.test", 0),
        DatabaseConfig("sqlite", path=str(db)),
        SafetyConfig(),
        str(metrics),
    )
    original = run_signature(config, cases, max_turns=8)
    assert run_signature(config, cases, max_turns=8) == original
    assert run_signature(replace(config, trace=False), cases, max_turns=8) == original
    assert (
        run_signature(replace(config, llm=replace(config.llm, temperature=1)), cases, max_turns=8)
        != original
    )
    cases.write_text("cases: []\n# revised")
    assert run_signature(config, cases, max_turns=8) != original
    cases.write_text("cases: []")
    metrics.write_text("metrics: [revised]")
    assert run_signature(config, cases, max_turns=8) != original
    metrics.write_text("metrics: []")
    db.write_bytes(b"snapshot two")
    assert run_signature(config, cases, max_turns=8) != original
