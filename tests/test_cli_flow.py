"""CLI-level tests for ``queryagent flow``: the gate, as a user meets it.

These go through ``main()`` so they cover exit codes and stderr the way a
person (or a script) actually experiences them. The recurring assertion is
the same one as everywhere else in slice 1A: when the flow refuses, the
database was not touched.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from queryagent.cli import main

CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: {db}
metrics_path: {metrics}
workflow:
  mappings_path: {mappings}
  state_path: {state}
trace: false
"""

METRICS = """\
metrics:
  - name: new_users
    display_name: 新增用户
    definition: 统计新加入的用户数；归属日期取法见 variants。
    tables: [users]
    variants:
      - key: registered
        label: 注册口径
        definition: 按 created_at 归属日期计数
      - key: first_order
        label: 首单口径
        definition: 按 first_order_at 归属日期计数
  - name: unmapped_metric
    display_name: 未映射指标
    definition: 维护者尚未声明查询映射的指标。
"""

MAPPINGS = """\
mappings:
  - metric: new_users
    variant: registered
    sql: SELECT COUNT(*) AS n FROM users
  - metric: new_users
    variant: first_order
    sql: SELECT COUNT(*) AS n FROM users WHERE first_order_at IS NOT NULL
"""


@pytest.fixture
def config(tmp_path: Path) -> Path:
    db = tmp_path / "shop.db"
    connection = sqlite3.connect(db)
    connection.execute("CREATE TABLE users (id INTEGER, first_order_at TEXT)")
    connection.executemany(
        "INSERT INTO users VALUES (?,?)", [(1, "2026-01-01"), (2, None), (3, None)]
    )
    connection.commit()
    connection.close()
    (tmp_path / "metrics.yaml").write_text(METRICS, encoding="utf-8")
    (tmp_path / "mappings.yaml").write_text(MAPPINGS, encoding="utf-8")
    path = tmp_path / "config.yaml"
    path.write_text(
        CONFIG.format(
            db=db,
            metrics=tmp_path / "metrics.yaml",
            mappings=tmp_path / "mappings.yaml",
            state=tmp_path / "workflow.db",
        ),
        encoding="utf-8",
    )
    return path


def _flow(config: Path, *extra: str) -> int:
    return main(["flow", "新增用户有多少？", "--config", str(config), *extra])


def test_declining_the_confirmation_executes_nothing(
    config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The default answer is no, and no is not an error the user must debug."""
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert _flow(config, "--variant", "registered") == 2
    out = capsys.readouterr().out
    assert "没有执行任何查询" in out
    assert "n\n" not in out  # no result block


def test_confirming_runs_the_mapped_query_for_that_variant(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _flow(config, "--variant", "first_order", "--yes") == 0
    out = capsys.readouterr().out
    assert "首单口径" in out
    assert "first_order_at IS NOT NULL" in out


def test_the_two_variants_give_different_numbers(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Same question, two 口径 — the disagreement the product is about."""
    assert _flow(config, "--variant", "registered", "--yes") == 0
    registered = capsys.readouterr().out
    assert _flow(config, "--variant", "first_order", "--yes") == 0
    first_order = capsys.readouterr().out
    assert "3" in registered.split("n\n")[-1]
    assert "1" in first_order.split("n\n")[-1]


def test_an_unknown_variant_is_refused_and_lists_the_real_ones(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _flow(config, "--variant", "whatever", "--yes") == 2
    assert "registered" in capsys.readouterr().err


def test_a_metric_without_a_mapping_is_refused_after_confirmation(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T14: the user may confirm it; the maintainer still has to map it."""
    code = main(["flow", "未映射指标是多少？", "--config", str(config), "--yes"])
    assert code == 2
    err = capsys.readouterr().err
    assert "no maintainer-defined query mapping" in err
    # The advice must name the person who can fix it, not tell the user to retry.
    assert "维护者" in err


def test_a_missing_mappings_file_is_reported_before_anything_runs(
    tmp_path: Path, config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = config.read_text(encoding="utf-8").replace(
        str(tmp_path / "mappings.yaml"), str(tmp_path / "nope.yaml")
    )
    config.write_text(text, encoding="utf-8")
    assert _flow(config, "--variant", "registered", "--yes") == 2
    assert "找不到文件" in capsys.readouterr().err


def test_the_confirmation_sheet_marks_where_each_rule_came_from(
    config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """D07: a user's own choice must never read as documented fact."""
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    _flow(config, "--variant", "registered")
    out = capsys.readouterr().out
    assert "[系统映射]" in out
    assert "[本次约定]" in out


def test_kb_import_with_embedding_configured_names_the_missing_key_before_any_work(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The embedding key is a second credential; missing it must be actionable.

    And it must fail before indexing anything: half the sources imported with
    vectors and half without is the state that makes semantic results quietly
    depend on import order.
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# 新增用户\n\n按注册日期计数。\n", encoding="utf-8")
    config.write_text(
        config.read_text(encoding="utf-8")
        + f"knowledge:\n  root: {tmp_path}\n  index_path: {tmp_path / 'kb.db'}\n"
        f"  sources:\n    - path: {docs}\n      workspace: ops\n"
        "  embedding:\n    base_url: https://x.invalid/v1\n    model: m\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("QUERYAGENT_EMBEDDING_API_KEY", raising=False)
    assert main(["kb", "import", "--config", str(config)]) == 2
    out, err = capsys.readouterr()
    assert "QUERYAGENT_EMBEDDING_API_KEY" in err
    assert "已纳入" not in out
