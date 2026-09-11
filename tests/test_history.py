"""Slice 1D: a choice this subject confirmed before, offered again (T42).

Offered, marked and dated; one person's, in one workspace; fills gaps and
overrides nothing; lapses when what it was about has moved. The CLI tests at
the end check the one place it is not offered at all: where nobody reads the
sheet.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from queryagent.cli import main
from queryagent.connectors.base import QueryResult
from queryagent.knowledge.models import RefStatus
from queryagent.metrics.base import Metric, MetricVariant
from queryagent.workflow.builder import MetricDraftBuilder
from queryagent.workflow.compiler import CompiledQuery, TemplateCompiler
from queryagent.workflow.evidence_builder import CompositeDraftBuilder
from queryagent.workflow.history import HistoryDraftBuilder
from queryagent.workflow.mappings import QueryMapping
from queryagent.workflow.models import (
    PERIOD_RULE_KEY,
    PREVIOUS_CHOICE_KEY,
    VARIANT_RULE_KEY,
    ActorContext,
    BusinessDefinition,
    Candidate,
    DraftStatus,
    Rule,
    RuleSource,
)
from queryagent.workflow.render import render_draft, render_unenforced
from queryagent.workflow.service import DraftBuilder, QueryWorkflow
from queryagent.workflow.store import SqliteWorkflowStore

ALICE = ActorContext(subject_id="alice", workspace_id="ops")
ALICE_IN_FINANCE = ActorContext(subject_id="alice", workspace_id="finance")
BOB = ActorContext(subject_id="bob", workspace_id="ops")
SHANGHAI = ZoneInfo("Asia/Shanghai")
SEP_10 = datetime(2026, 9, 10, 4, 0, tzinfo=timezone.utc)  # noon in Shanghai
REF = "growth-handbook#3@10:30"

REGISTERED = MetricVariant("registered", "注册口径", "按 created_at")
FIRST_ORDER = MetricVariant("first_order", "首单口径", "按 first_order_at")
NEW_USERS = Metric(
    name="new_users",
    display_name="新增用户",
    definition="统计新加入的用户数。",
    variants=(REGISTERED, FIRST_ORDER),
)
MAPPINGS = {
    ("new_users", "registered"): QueryMapping(
        source="users", measure="COUNT(*)", label="n", time_column="created_at"
    ),
    ("new_users", "first_order"): QueryMapping(
        source="users", measure="COUNT(*)", label="n", time_column="first_order_at"
    ),
}
PICK_FIRST_ORDER = Rule(VARIANT_RULE_KEY, "first_order", RuleSource.USER)
ADOPT_GROWTH = Rule(
    "counting_basis",
    "按首单日期计数",
    RuleSource.USER,
    evidence_ref=REF,
    note="采用文档写法",
    implies=("first_order",),
)


class Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


class _Metrics:
    def __init__(self, metric: Metric) -> None:
        self._metric = metric

    def match(self, question: str, top_k: int = 3) -> list[Metric]:
        return [self._metric]

    def get(self, name: str) -> Metric | None:
        return self._metric


class _Executor:
    def run(self, query: CompiledQuery) -> QueryResult:
        return QueryResult(("n",), ((7,),), elapsed_ms=1, truncated=False)


class Checker:
    """Stands in for the document provider's re-check."""

    def __init__(self, status: RefStatus = RefStatus.OK) -> None:
        self.status = status

    def check_refs(self, scope: object, refs: tuple[object, ...]) -> tuple[RefStatus, ...]:
        return tuple(self.status for _ in refs)


class Disagreeing:
    """Two handbooks disagree on the counting basis; the growth one points at first_order."""

    def build(self, question: str, actor: ActorContext | None = None) -> BusinessDefinition:
        return BusinessDefinition(
            "new_users",
            "新增用户",
            missing=(VARIANT_RULE_KEY, "counting_basis"),
            candidates=(
                Candidate("registered", "注册口径", "按 created_at"),
                Candidate("first_order", "首单口径", "按 first_order_at"),
                Candidate(
                    "counting_basis:0",
                    "运营手册",
                    "按注册日期计数",
                    evidence_ref="ops-handbook#1@0:8",
                    implies=("registered",),
                ),
                Candidate(
                    "counting_basis:1",
                    "增长手册",
                    "按首单日期计数",
                    evidence_ref=REF,
                    implies=("first_order",),
                ),
            ),
        )


class Documented:
    """The documents now agree on registered: it arrives as 「文档依据」."""

    def build(self, question: str, actor: ActorContext | None = None) -> BusinessDefinition:
        return BusinessDefinition(
            "new_users",
            "新增用户",
            rules=(
                Rule(
                    VARIANT_RULE_KEY,
                    "registered",
                    RuleSource.DOC,
                    evidence_ref="ops-handbook#1@0:8",
                    note="由文档依据对应",
                ),
            ),
            candidates=(
                Candidate("registered", "注册口径", "按 created_at"),
                Candidate("first_order", "首单口径", "按 first_order_at"),
            ),
        )


def _setup(
    tmp_path: Path,
    *,
    metric: Metric = NEW_USERS,
    mappings: dict[tuple[str, str], QueryMapping] = MAPPINGS,
    inner: DraftBuilder | None = None,
    checker: Checker | None = None,
    clock: Clock | None = None,
    max_age_days: int = 90,
) -> tuple[QueryWorkflow, Clock]:
    store = SqliteWorkflowStore(tmp_path / "wf.db")
    compiler = TemplateCompiler(mappings)
    clock = clock or Clock(SEP_10)
    base = inner or CompositeDraftBuilder(
        MetricDraftBuilder(_Metrics(metric), today=lambda: SEP_10.date()), None
    )
    builder = HistoryDraftBuilder(
        base,
        store,
        fingerprint=compiler.fingerprint,
        ref_checker=checker,
        zone=SHANGHAI,
        max_age_days=max_age_days,
        clock=clock,
    )
    workflow = QueryWorkflow(
        store=store,
        builder=builder,
        compiler=compiler,
        executor=_Executor().run,
        clock=clock,
        ref_checker=checker,
    )
    return workflow, clock


def _confirm_and_run(
    workflow: QueryWorkflow, actor: ActorContext, question: str, *rules: Rule
) -> str:
    draft = workflow.prepare(actor, question, request_id="r1")
    if rules:
        draft = workflow.amend(actor, draft.draft_id, expected_version=draft.version, rules=rules)
    confirmation = workflow.confirm(
        actor, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    workflow.execute(actor, confirmation.confirmation_id, idempotency_key=draft.draft_id)
    return draft.draft_id


def _open(workflow: QueryWorkflow, actor: ActorContext = ALICE) -> BusinessDefinition:
    return workflow.prepare(actor, "上个月新增用户", request_id="r2").definition


# ------------------------------------------------------------ offered, marked


def test_a_choice_confirmed_and_run_is_offered_again_marked_and_dated(tmp_path: Path) -> None:
    """G12: 「历史选择」 and the day it was confirmed — not 「本次约定」, not 「文档依据」."""
    workflow, clock = _setup(tmp_path)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    clock.at += timedelta(days=1)
    draft = workflow.prepare(ALICE, "上个月新增用户", request_id="r2")
    rule = draft.definition.rule(VARIANT_RULE_KEY)
    assert rule is not None
    assert (rule.value, rule.source) == ("first_order", RuleSource.HISTORY)
    assert draft.status is DraftStatus.AWAITING_CONFIRMATION
    assert (
        "  · 选定口径：首单口径 — 按 first_order_at（沿用你 2026-09-10 确认过的选择）    [历史选择]"
        in render_draft(draft)
    )


def test_a_remembered_choice_is_part_of_what_is_confirmed() -> None:
    """G12: repeating a choice and making it again are different acts, so different hashes."""
    base = BusinessDefinition(
        "m", "m", missing=(VARIANT_RULE_KEY,), candidates=(Candidate("a", "A", "A"),)
    )
    offered = base.with_rules((Rule(VARIANT_RULE_KEY, "a", RuleSource.HISTORY, note="沿用"),))
    chosen = base.with_rules((Rule(VARIANT_RULE_KEY, "a", RuleSource.USER),))
    assert offered.content_hash() != chosen.content_hash()
    with pytest.raises(ValueError, match="which earlier choice"):
        Rule(VARIANT_RULE_KEY, "a", RuleSource.HISTORY)


def test_history_is_one_persons_in_one_workspace(tmp_path: Path) -> None:
    """G13: never another subject's, never another workspace's — no standard by accident."""
    workflow, _ = _setup(tmp_path)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    for actor in (BOB, ALICE_IN_FINANCE):
        assert VARIANT_RULE_KEY in _open(workflow, actor).missing


def test_the_users_own_words_for_a_gap_are_offered_again(tmp_path: Path) -> None:
    metric = Metric(
        name="new_users",
        display_name="新增用户",
        definition="统计新加入的用户数。",
        variants=(REGISTERED, FIRST_ORDER),
        required_rules=("refund_handling",),
    )
    workflow, _ = _setup(tmp_path, metric=metric)
    written = Rule("refund_handling", "退款订单不计入", RuleSource.USER)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER, written)
    definition = _open(workflow)
    rule = definition.rule("refund_handling")
    assert rule is not None and (rule.value, rule.source) == ("退款订单不计入", RuleSource.HISTORY)
    assert definition.missing == ()


def test_an_adopted_document_wording_is_offered_while_the_document_checks_out(
    tmp_path: Path,
) -> None:
    workflow, _ = _setup(tmp_path, inner=Disagreeing(), checker=Checker())
    _confirm_and_run(workflow, ALICE, "新增用户", ADOPT_GROWTH, PICK_FIRST_ORDER)
    definition = _open(workflow)
    rule = definition.rule("counting_basis")
    assert rule is not None
    assert (rule.source, rule.evidence_ref, rule.implies) == (
        RuleSource.HISTORY,
        REF,
        ("first_order",),
    )
    assert definition.missing == ()


# ------------------------------------------------------------ gaps, not over


def test_history_fills_gaps_and_never_overrides_the_documents_or_the_question(
    tmp_path: Path,
) -> None:
    """G15/E12: the documents' reading stays and the old one is shown beside it;
    「上个月」 belonged to the old question and does not come back."""
    workflow, _ = _setup(tmp_path)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    later, _ = _setup(tmp_path, inner=Documented())
    draft = later.prepare(ALICE, "新增用户有多少", request_id="r2")
    definition = draft.definition
    chosen = definition.rule(VARIANT_RULE_KEY)
    assert chosen is not None and (chosen.value, chosen.source) == ("registered", RuleSource.DOC)
    previous = definition.rule(PREVIOUS_CHOICE_KEY)
    assert previous is not None
    assert previous.value == "首单口径（你 2026-09-10 确认过；与本次的文档依据不同，未沿用）"
    assert definition.rule(PERIOD_RULE_KEY) is None
    assert "  · 上次的选择：首单口径（" in render_draft(draft)
    assert render_unenforced(definition) == ""


# ------------------------------------------------------------------- lapses


def test_a_changed_mapping_ends_the_history(tmp_path: Path) -> None:
    """G14: the same reading's name over different SQL is not the same choice."""
    workflow, _ = _setup(tmp_path)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    changed = dict(MAPPINGS)
    changed[("new_users", "first_order")] = QueryMapping(
        source="users",
        measure="COUNT(*)",
        label="n",
        time_column="first_order_at",
        where=("channel <> 'internal_test'",),
    )
    later, _ = _setup(tmp_path, mappings=changed)
    assert VARIANT_RULE_KEY in _open(later).missing


def test_an_option_no_longer_offered_is_not_offered_from_memory(tmp_path: Path) -> None:
    workflow, _ = _setup(tmp_path)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    trimmed = Metric(
        name="new_users", display_name="新增用户", definition="统计新加入的用户数。",
        variants=(REGISTERED, MetricVariant("first_paid", "首付口径", "按首次支付")),
    )  # fmt: skip
    later, _ = _setup(tmp_path, metric=trimmed)
    assert VARIANT_RULE_KEY in _open(later).missing


def test_a_choice_older_than_the_limit_lapses(tmp_path: Path) -> None:
    workflow, clock = _setup(tmp_path, max_age_days=30)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    clock.at += timedelta(days=31)
    assert VARIANT_RULE_KEY in _open(workflow).missing


def test_a_choice_resting_on_a_withdrawn_document_is_not_offered_and_not_explained(
    tmp_path: Path,
) -> None:
    """G14: not offered, and not explained — which document lapsed can itself disclose one."""
    checker = Checker()
    workflow, _ = _setup(tmp_path, inner=Disagreeing(), checker=checker)
    _confirm_and_run(workflow, ALICE, "新增用户", ADOPT_GROWTH, PICK_FIRST_ORDER)
    checker.status = RefStatus.UNAVAILABLE
    definition = _open(workflow)
    assert "counting_basis" in definition.missing
    assert all(rule.evidence_ref != REF for rule in definition.rules)


def test_a_run_recorded_before_fingerprints_is_never_offered(tmp_path: Path) -> None:
    """G16: a v0.8 run cannot say whether its mapping changed, so it is not trusted to."""
    workflow, _ = _setup(tmp_path)
    _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    connection = sqlite3.connect(tmp_path / "wf.db")
    connection.execute("UPDATE runs SET mapping_fingerprint = ''")
    connection.commit()
    connection.close()
    assert VARIANT_RULE_KEY in _open(workflow).missing


def test_a_draft_amended_after_its_run_no_longer_holds_what_was_approved(tmp_path: Path) -> None:
    workflow, _ = _setup(tmp_path)
    draft_id = _confirm_and_run(workflow, ALICE, "上个月新增用户", PICK_FIRST_ORDER)
    current = workflow.get_draft(ALICE, draft_id)
    workflow.amend(
        ALICE,
        draft_id,
        expected_version=current.version,
        rules=(Rule(VARIANT_RULE_KEY, "registered", RuleSource.USER),),
    )
    assert VARIANT_RULE_KEY in _open(workflow).missing


# ---------------------------------------------------------------------- CLI

CLI_CONFIG = """\
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

METRICS_YAML = """\
metrics:
  - name: new_users
    display_name: 新增用户
    definition: 统计新加入的用户数。
    variants:
      - key: registered
        label: 注册口径
        definition: 按 created_at 归属日期计数
      - key: first_order
        label: 首单口径
        definition: 按 first_order_at 归属日期计数
"""

MAPPINGS_YAML = """\
mappings:
  - metric: new_users
    variant: registered
    sql: SELECT COUNT(*) AS n FROM users
  - metric: new_users
    variant: first_order
    sql: SELECT COUNT(*) AS n FROM users WHERE first_order_at IS NOT NULL
"""


@pytest.fixture
def cli_config(tmp_path: Path) -> Path:
    connection = sqlite3.connect(tmp_path / "shop.db")
    connection.execute("CREATE TABLE users (id INTEGER, first_order_at TEXT)")
    connection.executemany("INSERT INTO users VALUES (?,?)", [(1, "2026-01-01"), (2, None)])
    connection.commit()
    connection.close()
    (tmp_path / "metrics.yaml").write_text(METRICS_YAML, encoding="utf-8")
    (tmp_path / "mappings.yaml").write_text(MAPPINGS_YAML, encoding="utf-8")
    path = tmp_path / "config.yaml"
    path.write_text(
        CLI_CONFIG.format(
            db=tmp_path / "shop.db",
            metrics=tmp_path / "metrics.yaml",
            mappings=tmp_path / "mappings.yaml",
            state=tmp_path / "workflow.db",
        ),
        encoding="utf-8",
    )
    return path


def _flow(config: Path, *extra: str) -> int:
    return main(["flow", "新增用户有多少？", "--config", str(config), *extra])


def _runs(config: Path) -> int:
    connection = sqlite3.connect(config.parent / "workflow.db")
    (count,) = connection.execute("SELECT COUNT(*) FROM runs").fetchone()
    connection.close()
    return int(count)


def test_with_yes_nothing_remembered_fills_the_sheet(
    cli_config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """E14/G16: nobody reads a --yes sheet, so nothing remembered goes on it."""
    assert _flow(cli_config, "--variant", "first_order", "--yes") == 0
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert _flow(cli_config, "--yes") == 2
    assert "未选择口径" in capsys.readouterr().out
    assert _runs(cli_config) == 1


def test_at_the_prompt_the_remembered_reading_is_on_the_sheet_and_confirmed_there(
    cli_config: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _flow(cli_config, "--variant", "first_order", "--yes") == 0
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")
    assert _flow(cli_config) == 0
    out = capsys.readouterr().out
    assert "首单口径" in out and "[历史选择]" in out
    assert _runs(cli_config) == 2


def test_no_history_asks_again(cli_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert _flow(cli_config, "--variant", "first_order", "--yes") == 0
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert _flow(cli_config, "--no-history") == 2
    assert _runs(cli_config) == 1
