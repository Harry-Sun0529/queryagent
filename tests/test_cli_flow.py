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


# ------------------------------------------- T03: handbooks that disagree

HANDBOOKS = {
    "运营手册.md": "# 运营手册\n\n## 新增用户\n\n新增用户按 users.created_at 的注册日期计数。\n",
    "增长周报.md": (
        "# 增长周报\n\n## 新增用户\n\n"
        "新增用户按 users.first_order_at 的首单日期计数。\n"
    ),
}


class _CitingLLM:
    """Emits one rule per excerpt, citing each by the number the prompt gave it.

    Registered-date rules are emitted first so candidate numbering is stable
    regardless of retrieval order: counting_basis:0 is always 按注册日期计数.
    """

    def complete(self, messages, tools=None, **kwargs):  # type: ignore[no-untyped-def]
        import json
        import re

        from queryagent.llm.base import ModelResponse

        blocks = re.findall(
            r"<<<EVIDENCE (\d+)>>>\n(.*?)<<<END EVIDENCE", messages[-1].content, re.S
        )
        rules = []
        readings = (("created_at", "按注册日期计数"), ("first_order_at", "按首单日期计数"))
        for column, value in readings:
            for index, body in blocks:
                found = re.search(rf"新增用户按 users\.{column} 的\S+?计数", body)
                if found:
                    rules.append(
                        {
                            "key": "counting_basis",
                            "value": value,
                            "citation": int(index),
                            "quote": found.group(0),
                        }
                    )
        return ModelResponse(
            text=json.dumps({"rules": rules}, ensure_ascii=False),
            tool_calls=(),
            stop_reason="end_turn",
            usage=None,
        )


def _with_disagreeing_handbooks(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    names: tuple[str, ...] = tuple(HANDBOOKS),
) -> None:
    docs = tmp_path / "kb"
    docs.mkdir()
    for name in names:
        (docs / name).write_text(HANDBOOKS[name], encoding="utf-8")
    config.write_text(
        config.read_text(encoding="utf-8")
        + f"knowledge:\n  root: {tmp_path}\n  index_path: {tmp_path / 'kb.db'}\n"
        f"  sources:\n    - path: {docs}\n      workspace: ops\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("queryagent.cli.make_backend", lambda _llm: _CitingLLM())
    assert main(["kb", "import", "--config", str(config)]) == 0


def _flow_ops(config: Path, *extra: str) -> int:
    return main(
        ["flow", "新增用户有多少？", "--config", str(config), "--workspace", "ops", *extra]
    )


def test_two_handbooks_that_disagree_are_both_shown_and_nothing_runs(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T03 end to end: both readings on the sheet, each with its source."""
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch)
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert _flow_ops(config, "--variant", "registered", "--yes") == 2
    out = capsys.readouterr().out
    assert "文档之间的分歧 · 统计口径" in out
    assert "运营手册.md" in out
    assert "增长周报.md" in out
    assert "没有执行任何查询" in out


def test_adopting_a_handbook_records_the_users_choice_with_that_source(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D07: the words are the handbook's, the decision is the user's."""
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch)
    capsys.readouterr()
    code = _flow_ops(config, "--variant", "registered", "--adopt", "counting_basis:0", "--yes")
    out = capsys.readouterr().out
    assert code == 0
    final_sheet = out[out.rfind("口径确认单") : out.find("结果（")]
    assert "统计口径：按注册日期计数    [本次约定]" in final_sheet
    assert "出处：运营手册.md" in final_sheet
    assert "已采用其中一种" in final_sheet
    assert "  3" in out.split("结果（")[1]


def test_an_unknown_adopt_key_is_refused_and_lists_the_real_ones(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch)
    capsys.readouterr()
    assert _flow_ops(config, "--variant", "registered", "--adopt", "counting_basis:9", "--yes") == 2
    assert "counting_basis:0" in capsys.readouterr().err


def test_the_result_line_claims_only_what_the_query_executed(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Document rules explain the 口径; the maintainer mapping is what runs.

    A live run printed 「统计周期=按自然月」 in the result line above an
    all-time COUNT — the number claimed a rule its query never applied.
    """
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch)
    capsys.readouterr()
    _flow_ops(config, "--variant", "registered", "--adopt", "counting_basis:0", "--yes")
    out = capsys.readouterr().out
    recap = out.split("结果（")[1].splitlines()[0]
    assert "选定口径=注册口径" in recap
    assert "统计口径" not in recap
    assert "系统不核对两者是否一致" in out


# ------------------------------------ T39: document rules meet execution

ENFORCING_MAPPINGS = """\
mappings:
  - metric: new_users
    variant: registered
    from: users
    measure: COUNT(*)
    label: n
    enforces: {counting_basis: [created_at, 注册日期]}
  - metric: new_users
    variant: first_order
    from: users
    measure: COUNT(*)
    label: n
    where: ["first_order_at IS NOT NULL"]
    enforces: {counting_basis: [first_order_at, 首单日期]}
"""


def _no_prompt(prompt: str = "") -> str:
    raise AssertionError(f"asked when it should not have been: {prompt}")


def test_a_handbook_naming_one_reading_chooses_it_as_document_evidence(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F12: the handbook reaches the SQL by choosing a statement a maintainer wrote."""
    (tmp_path / "mappings.yaml").write_text(ENFORCING_MAPPINGS, encoding="utf-8")
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch, ("运营手册.md",))
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", _no_prompt)
    assert _flow_ops(config, "--yes") == 0
    out = capsys.readouterr().out
    assert "选定口径：注册口径 — 按 created_at 归属日期计数    [文档依据]" in out
    assert "→ 已由所选口径（注册口径）执行" in out
    assert "需要你选一个" not in out  # the choice is made; the sheet must not ask for it
    result = out.split("结果（")[1]
    assert "统计口径=按注册日期计数" in result.splitlines()[0]  # F14: counted as applied
    assert "系统不核对" not in out
    assert "  3" in result


def test_adopting_a_handbook_settles_which_reading_runs(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F13: adopting 增长周报's wording runs the first-order reading, unasked."""
    (tmp_path / "mappings.yaml").write_text(ENFORCING_MAPPINGS, encoding="utf-8")
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch)
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", _no_prompt)
    assert _flow_ops(config, "--adopt", "counting_basis:1", "--yes") == 0
    out = capsys.readouterr().out
    first_sheet = out[: out.find("口径确认单", 1)]
    assert "→ 对应可执行口径：注册口径" in first_sheet
    assert "→ 对应可执行口径：首单口径" in first_sheet
    final_sheet = out[out.rfind("口径确认单") : out.find("结果（")]
    assert "选定口径：首单口径" in final_sheet
    assert "  1" in out.split("结果（")[1]


def test_adopting_one_reading_and_naming_the_other_is_refused_before_any_query(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F13: two contradictory answers in one command; running either is a guess."""
    (tmp_path / "mappings.yaml").write_text(ENFORCING_MAPPINGS, encoding="utf-8")
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch)
    capsys.readouterr()
    code = _flow_ops(config, "--adopt", "counting_basis:0", "--variant", "first_order", "--yes")
    captured = capsys.readouterr()
    assert code == 2
    assert "两者矛盾" in captured.err
    assert "结果（" not in captured.out


def test_choosing_against_the_handbook_runs_the_choice_and_names_the_conflict(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """E12/F14: the user may overrule the handbook, but not without being told."""
    (tmp_path / "mappings.yaml").write_text(ENFORCING_MAPPINGS, encoding="utf-8")
    _with_disagreeing_handbooks(config, tmp_path, monkeypatch, ("运营手册.md",))
    capsys.readouterr()
    assert _flow_ops(config, "--variant", "first_order", "--yes") == 0
    out = capsys.readouterr().out
    assert "✗ 与所选口径不一致：这段原文对应「注册口径」，执行的是「首单口径」" in out
    result = out.split("结果（")[1]
    assert "与执行不一致：统计口径（原文对应「注册口径」）" in result
    assert "统计口径=" not in result.splitlines()[0]
    assert "  1" in result


def test_a_maintainer_only_result_carries_no_disclaimer(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing to disclaim when every confirmed rule is one the query applied."""
    assert _flow(config, "--variant", "first_order", "--yes") == 0
    assert "系统不核对" not in capsys.readouterr().out


# ------------------------------------------------- K7: rules nothing stated


def _require_time_window(tmp_path: Path) -> None:
    (tmp_path / "metrics.yaml").write_text(
        METRICS.replace(
            "    tables: [users]\n", "    tables: [users]\n    required_rules: [time_window]\n", 1
        ),
        encoding="utf-8",
    )


def test_a_rule_nothing_states_is_asked_for_and_marked_as_the_users(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """D07: the user states it; the sheet says so; the result does not claim it."""
    _require_time_window(tmp_path)
    code = _flow(config, "--variant", "registered", "--rule", "time_window=按自然月统计", "--yes")
    out = capsys.readouterr().out
    assert code == 0
    final_sheet = out[out.rfind("口径确认单") : out.find("结果（")]
    assert "统计周期：按自然月统计    [本次约定]" in final_sheet
    assert "统计周期" not in out.split("结果（")[1].splitlines()[0]
    assert "系统不核对两者是否一致" in out


def test_declining_to_state_a_required_rule_runs_nothing(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _require_time_window(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert _flow(config, "--variant", "registered", "--yes") == 2
    out = capsys.readouterr().out
    assert "尚未确定：" in out and "统计周期" in out
    assert "没有执行任何查询" in out


def test_a_rule_for_a_gap_that_does_not_exist_is_refused(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _require_time_window(tmp_path)
    assert _flow(config, "--variant", "registered", "--rule", "refund_handling=x", "--yes") == 2
    assert "time_window" in capsys.readouterr().err



# ------------------------------------------------------ P1/P2: 统计区间

# The fixture table has only first_order_at, so both readings use it here.
PERIOD_MAPPINGS = """\
mappings:
  - metric: new_users
    variant: registered
    from: users
    measure: COUNT(*)
    label: n
    time_column: first_order_at
  - metric: new_users
    variant: first_order
    from: users
    measure: COUNT(*)
    label: n
    time_column: first_order_at
    where: ["first_order_at IS NOT NULL"]
"""


def _require_period(tmp_path: Path) -> None:
    (tmp_path / "metrics.yaml").write_text(
        METRICS.replace(
            "    tables: [users]\n", "    tables: [users]\n    required_rules: [period]\n", 1
        ),
        encoding="utf-8",
    )
    (tmp_path / "mappings.yaml").write_text(PERIOD_MAPPINGS, encoding="utf-8")


def test_a_stated_period_is_confirmed_applied_and_claimed(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P1 via --period, and P8: the result line names the period it ran."""
    _require_period(tmp_path)
    code = _flow(
        config, "--variant", "registered", "--period", "2026-01-01..2026-01-31", "--yes"
    )
    out = capsys.readouterr().out
    assert code == 0
    final_sheet = out[out.rfind("口径确认单") : out.find("结果（")]
    assert "统计区间：2026-01-01 至 2026-01-31（31 天）" in final_sheet
    assert "first_order_at >= ? AND first_order_at < ?" in out
    assert "参数（按 ? 的顺序绑定）：2026-01-01, 2026-02-01" in out
    assert "数据新鲜度探测：SELECT MAX(first_order_at) FROM users" in out
    result = out.split("结果（")[1]
    assert "统计区间=2026-01-01 至 2026-01-31" in result.splitlines()[0]
    assert "  1" in result
    assert "系统不核对" not in out


def test_the_result_says_which_days_of_the_period_have_no_data(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F4 as the user meets it: the newest record is 2026-01-01, the period a month."""
    _require_period(tmp_path)
    assert _flow(config, "--variant", "registered", "--period", "2026-01", "--yes") == 0
    result = capsys.readouterr().out.split("结果（")[1]
    assert "数据不完整" in result
    assert "最后 30 天（2026-01-02 起）没有任何数据" in result


def test_a_period_after_the_data_reads_as_no_data_not_as_zero(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F5: COUNT says 0; the note says why that 0 is not the business doing nothing."""
    _require_period(tmp_path)
    assert _flow(config, "--variant", "registered", "--period", "2026-03", "--yes") == 0
    result = capsys.readouterr().out.split("结果（")[1]
    assert "  0" in result
    assert "早于统计区间的开始 2026-03-01" in result


def test_a_daily_split_lists_every_day_and_says_which_have_no_data(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F7/F8 as the user meets it: 「每天」 is confirmed, compiled, and filled in."""
    _require_period(tmp_path)
    code = main(
        [
            "flow",
            "每天新增用户有多少？",
            "--config",
            str(config),
            "--variant",
            "registered",
            "--period",
            "2026-01-01..2026-01-03",
            "--yes",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "分组方式：按天（每个日期一行）（由问题中的「每天」换算）" in out
    result = out.split("结果（")[1]
    assert "分组方式=按天" in result.splitlines()[0]
    assert "  2026-01-01 | 1" in result
    assert "  2026-01-02 | （无数据）" in result
    assert "GROUP BY date(first_order_at)" in result


def test_an_average_is_asked_about_and_can_be_answered_with_a_total(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F9: 「日均」 is not a split; the user says what they want, or nothing runs."""
    _require_period(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    args = [
        "flow",
        "日均新增用户有多少？",
        "--config",
        str(config),
        "--variant",
        "registered",
        "--period",
        "2026-01",
    ]
    assert main([*args, "--yes"]) == 2
    captured = capsys.readouterr()
    assert "没有执行任何查询" in captured.out
    assert "日均" in captured.err
    assert main([*args, "--group-by", "none", "--yes"]) == 0
    assert "分组方式=不分组" in capsys.readouterr().out


def test_the_questions_own_period_names_the_words_it_came_from(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _require_period(tmp_path)
    code = main(
        [
            "flow", "2026年1月新增用户有多少？", "--config", str(config),
            "--variant", "registered", "--yes",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "由问题中的「2026年1月」换算" in out
    # The fixture's one January row is a bare date; it has to be counted.
    assert "  1" in out.split("结果（")[1]


def test_a_required_period_nobody_states_runs_nothing(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _require_period(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert _flow(config, "--variant", "registered", "--yes") == 2
    out = capsys.readouterr().out
    assert "统计区间" in out.split("尚未确定：")[1]
    assert "没有执行任何查询" in out


def test_an_unreadable_period_is_refused_with_what_would_be_read(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A period typed but not understood must not quietly become no period."""
    _require_period(tmp_path)
    assert _flow(config, "--variant", "registered", "--period", "随便哪段", "--yes") == 2
    assert "上个月" in capsys.readouterr().err


def test_two_periods_in_a_question_are_named_and_asked_about(
    config: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """P2 at the CLI: the refusal says which words collided."""
    _require_period(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    code = main(
        [
            "flow", "2026年1月和2026年2月新增用户", "--config", str(config),
            "--variant", "registered", "--yes",
        ]
    )
    assert code == 2
    assert "多个不同的统计区间" in capsys.readouterr().err



# ------------------------------------------------------------ P9 / P10

EMPTY_SUM_MAPPINGS = """\
mappings:
  - metric: new_users
    variant: registered
    from: users
    measure: SUM(id)
    label: s
    time_column: first_order_at
"""


def test_a_result_without_a_period_says_it_is_unbounded(
    config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P9: no window is a fact about this number, not something to read off the SQL."""
    assert _flow(config, "--variant", "registered", "--yes") == 0
    recap = capsys.readouterr().out.split("结果（")[1].splitlines()[0]
    assert "统计区间=未限定（全部数据）" in recap


def test_an_empty_aggregate_says_it_is_empty_not_zero(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P10: SUM over no rows is NULL — bare it reads as a fault, as 0 it is a false claim.

    December 2025 lies inside the data (the newest record is 2026-01-01), so
    this is the "no matching records" case, not the "no data yet" one.
    """
    _require_period(tmp_path)
    (tmp_path / "mappings.yaml").write_text(EMPTY_SUM_MAPPINGS, encoding="utf-8")
    code = _flow(
        config, "--variant", "registered", "--period", "2025-12-01..2025-12-31", "--yes"
    )
    assert code == 0
    assert "空不等于 0" in capsys.readouterr().out


def test_an_empty_aggregate_after_the_data_ends_says_there_is_no_data_yet(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F5: 2030 is after the newest record, so there was nothing to match."""
    _require_period(tmp_path)
    (tmp_path / "mappings.yaml").write_text(EMPTY_SUM_MAPPINGS, encoding="utf-8")
    code = _flow(
        config, "--variant", "registered", "--period", "2030-01-01..2030-01-31", "--yes"
    )
    result = capsys.readouterr().out.split("结果（")[1]
    assert code == 0
    assert "结果为空：统计区间内还没有数据" in result
    assert "没有匹配的记录" not in result
    assert "不代表业务为 0" in result


def test_a_zero_count_is_an_answer_and_gets_no_note(
    config: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """COUNT's 0 means none were found — that is the answer, not an absence of one."""
    _require_period(tmp_path)
    code = _flow(
        config, "--variant", "registered", "--period", "2030-01-01..2030-01-31", "--yes"
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "  0" in out.split("结果（")[1]
    assert "空不等于" not in out
