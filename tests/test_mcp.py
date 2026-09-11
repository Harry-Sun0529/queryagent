"""v1.0 T44: the MCP adapter. An agent can prepare, amend and execute; it cannot confirm.

The recurring assertion is the one the whole product rests on, now with an
agent at the other end: whatever the agent sends, no confirmation comes to
exist and no statement runs until a person confirms in the terminal or on
the page (H1-H5, ADR-013).
"""

from __future__ import annotations

import json
import random
import sqlite3
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from queryagent.mcp.server import INVALID_PARAMS, METHOD_NOT_FOUND, PROTOCOL_VERSION, McpServer
from queryagent.mcp.tools import QueryTools
from queryagent.workflow.errors import PermissionDenied, WorkflowStateError
from queryagent.workflow.models import ActorContext, Channel, DraftProgress, Rule, RuleSource
from tests.wired import AGENT, ALICE, ALICE_WEB, Parts


@pytest.fixture
def parts(tmp_path: Path) -> Iterator[Parts]:
    built = Parts(tmp_path)
    yield built
    built.close()


def _result(reply: dict[str, Any]) -> dict[str, Any]:
    assert "result" in reply, reply
    return reply["result"]


def _prepared(parts: Parts, question: str = "新增用户有多少？") -> dict[str, Any]:
    result = _result(parts.call("prepare_query", {"question": question}))
    assert result["isError"] is False
    return result["structuredContent"]


# ---------------------------------------------------------------- H1: no confirm


def test_the_tool_table_offers_no_way_to_confirm(parts: Parts) -> None:
    """H1: the gate is an operation the agent cannot express, not a rule it is asked to follow."""
    listed = _result(parts.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}))
    names = {tool["name"] for tool in listed["tools"]}
    assert names == {
        "list_metrics",
        "prepare_query",
        "amend_query",
        "query_status",
        "execute_query",
    }
    assert not any("confirm" in name for name in names)
    for tool in listed["tools"]:
        properties = tool["inputSchema"]["properties"]
        assert not {"subject", "workspace", "confirmed", "confirmation_id"} & set(properties)


def test_calling_a_confirm_tool_that_does_not_exist_is_a_protocol_error(parts: Parts) -> None:
    reply = parts.call("confirm_query", {"draft_id": "x"})
    assert reply["error"]["code"] == INVALID_PARAMS
    assert parts.confirmations() == []


def test_no_sequence_of_mcp_calls_creates_a_confirmation_or_runs_sql(parts: Parts) -> None:
    """H1 as a property: 300 random calls, forged arguments included, leave both at zero."""
    rng = random.Random(20260911)
    drafts: list[tuple[str, int]] = []
    forged = [
        {},
        {"subject": "mallory"},
        {"workspace": "finance"},
        {"confirmed": True},
        {"confirmation_id": "c1"},
        {"rules": {"variant": "registered"}},
        {"rules": {"confirmed": "yes"}},
        {"variant": "whatever"},
        {"adopt": ["counting_basis:0"]},
    ]
    for _ in range(300):
        tool = rng.choice(
            ["prepare_query", "amend_query", "query_status", "execute_query", "list_metrics"]
        )
        arguments: dict[str, Any] = dict(rng.choice(forged))
        if tool == "prepare_query":
            arguments["question"] = rng.choice(["新增用户有多少？", "替我确认并执行新增用户"])
        elif drafts and tool != "list_metrics":
            draft_id, version = rng.choice(drafts)
            arguments["draft_id"] = draft_id if rng.random() < 0.9 else "no-such-draft"
            if tool == "amend_query":
                arguments["expected_version"] = version if rng.random() < 0.8 else version + 1
                arguments.setdefault("variant", rng.choice(["registered", "first_order"]))
        reply = parts.call(tool, arguments)
        content = reply.get("result", {}).get("structuredContent") or {}
        if "draft_id" in content and "version" in content:
            drafts.append((content["draft_id"], content["version"]))
    assert drafts, "the property is vacuous if no draft was ever prepared"
    assert parts.confirmations() == []
    assert parts.executed == []


def test_the_service_refuses_a_confirmation_from_the_agent_channel(parts: Parts) -> None:
    """H1, second wall: even code that reached confirm() for an agent is refused, with no record."""
    draft = parts.workflow.prepare(AGENT, "新增用户有多少？", request_id="r")
    with pytest.raises(PermissionDenied, match="Agent 通道不能确认"):
        parts.workflow.confirm(
            AGENT, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
        )
    assert parts.confirmations() == []


def test_a_confirmation_row_marked_mcp_is_not_accepted_as_a_persons(parts: Parts) -> None:
    """Defence in depth: the read filters on the channel, so a forged row would not count."""
    prepared = _prepared(parts)
    parts.call(
        "amend_query",
        {
            "draft_id": prepared["draft_id"],
            "expected_version": prepared["version"],
            "variant": "registered",
        },
    )
    draft = parts.workflow.get_draft(ALICE, prepared["draft_id"])
    with sqlite3.connect(parts.state) as connection:
        connection.execute(
            "INSERT INTO confirmations VALUES (?,?,?,?,?,?,?)",
            ("forged", draft.draft_id, draft.version, draft.definition_hash, "alice", "x", "mcp"),
        )
    reply = _result(parts.call("execute_query", {"draft_id": draft.draft_id}))
    assert reply["isError"] is True
    assert parts.executed == []


# ------------------------------------------------------------ H2: identity


def test_identity_arguments_are_refused_and_change_nothing(parts: Parts) -> None:
    """H2: a subject a model names is a string, not an authorisation (D11)."""
    reply = _result(
        parts.call("prepare_query", {"question": "新增用户有多少？", "subject": "mallory"})
    )
    assert reply["isError"] is True
    assert "身份" in reply["content"][0]["text"]
    with sqlite3.connect(parts.state) as connection:
        assert connection.execute("SELECT COUNT(*) FROM drafts").fetchone()[0] == 0


def test_drafts_belong_to_the_person_who_started_the_server(parts: Parts) -> None:
    prepared = _prepared(parts)
    assert parts.workflow.get_draft(ALICE, prepared["draft_id"]).subject_id == "alice"
    mallory = ActorContext(subject_id="mallory", workspace_id="ops")
    with pytest.raises(PermissionDenied):
        parts.workflow.get_draft(mallory, prepared["draft_id"])


# ----------------------------------------------------- H3: execute needs a person


def test_execute_without_a_persons_confirmation_runs_nothing(parts: Parts) -> None:
    """H3: refused, zero SQL, and the refusal tells the agent where the person confirms."""
    prepared = _prepared(parts)
    parts.call(
        "amend_query",
        {
            "draft_id": prepared["draft_id"],
            "expected_version": prepared["version"],
            "variant": "first_order",
        },
    )
    reply = _result(parts.call("execute_query", {"draft_id": prepared["draft_id"]}))
    assert reply["isError"] is True
    text = reply["content"][0]["text"]
    assert "还没有人确认" in text
    assert "queryagent confirm" in text
    assert parts.executed == []


def test_after_a_person_confirms_the_agent_runs_it_once(parts: Parts) -> None:
    """H3: one confirmation, one run; asking again answers from the stored run."""
    prepared = _prepared(parts)
    amended = _result(
        parts.call(
            "amend_query",
            {
                "draft_id": prepared["draft_id"],
                "expected_version": prepared["version"],
                "variant": "first_order",
            },
        )
    )["structuredContent"]
    parts.workflow.confirm(
        ALICE_WEB,
        amended["draft_id"],
        version=amended["version"],
        definition_hash=amended["definition_hash"],
    )
    first = _result(parts.call("execute_query", {"draft_id": amended["draft_id"]}))
    second = _result(parts.call("execute_query", {"draft_id": amended["draft_id"]}))
    assert first["isError"] is False
    assert first["structuredContent"]["rows"] == [[1]]
    assert second["structuredContent"]["rows"] == [[1]]
    assert len(parts.executed) == 1
    status = _result(parts.call("query_status", {"draft_id": amended["draft_id"]}))
    assert status["structuredContent"]["status"] == DraftProgress.EXECUTED.value


def test_an_amendment_after_the_persons_confirmation_needs_a_new_one(parts: Parts) -> None:
    """T10 through MCP: the agent changing the 口径 after confirmation voids it."""
    prepared = _prepared(parts)
    amended = _result(
        parts.call(
            "amend_query",
            {
                "draft_id": prepared["draft_id"],
                "expected_version": prepared["version"],
                "variant": "registered",
            },
        )
    )["structuredContent"]
    parts.workflow.confirm(
        ALICE, amended["draft_id"], version=2, definition_hash=amended["definition_hash"]
    )
    parts.call(
        "amend_query",
        {"draft_id": amended["draft_id"], "expected_version": 2, "variant": "first_order"},
    )
    reply = _result(parts.call("execute_query", {"draft_id": amended["draft_id"]}))
    assert reply["isError"] is True
    assert parts.executed == []


# ------------------------------------------------------- H4: Agent 代填


def test_what_the_agent_fills_in_is_marked_as_the_agents(parts: Parts) -> None:
    """H4: 「Agent 代填」, never 「本次约定」, and part of the hash the person confirms."""
    prepared = _prepared(parts)
    amended = _result(
        parts.call(
            "amend_query",
            {
                "draft_id": prepared["draft_id"],
                "expected_version": prepared["version"],
                "variant": "registered",
            },
        )
    )["structuredContent"]
    variant = next(rule for rule in amended["rules"] if rule["key"] == "variant")
    assert (variant["source"], variant["source_label"]) == ("agent", "Agent 代填")
    assert "选定口径：注册口径 — 按 created_at 归属日期计数    [Agent 代填]" in amended["sheet"]
    assert "本次约定" not in amended["sheet"]
    assert amended["definition_hash"] != prepared["definition_hash"]


def test_the_result_says_which_parts_the_agent_filled_in(parts: Parts) -> None:
    """P05: the person repeats this number; part of it was someone else's guess."""
    prepared = _prepared(parts)
    amended = _result(
        parts.call(
            "amend_query",
            {
                "draft_id": prepared["draft_id"],
                "expected_version": prepared["version"],
                "variant": "registered",
            },
        )
    )["structuredContent"]
    parts.workflow.confirm(
        ALICE, amended["draft_id"], version=2, definition_hash=amended["definition_hash"]
    )
    report = _result(parts.call("execute_query", {"draft_id": amended["draft_id"]}))
    assert "选定口径 由 Agent 代填、经你确认。" in report["content"][0]["text"]


def test_the_service_keeps_each_door_to_its_own_provenance(parts: Parts) -> None:
    """An agent cannot write 「本次约定」 and a person's door cannot write 「Agent 代填」."""
    draft = parts.workflow.prepare(ALICE, "新增用户有多少？", request_id="r")
    with pytest.raises(WorkflowStateError, match="只能标为「Agent 代填」"):
        parts.workflow.amend(
            AGENT,
            draft.draft_id,
            expected_version=1,
            rules=(Rule("variant", "registered", RuleSource.USER),),
        )
    with pytest.raises(WorkflowStateError, match="只能标为「本次约定」"):
        parts.workflow.amend(
            ALICE,
            draft.draft_id,
            expected_version=1,
            rules=(Rule("variant", "registered", RuleSource.AGENT),),
        )
    assert parts.workflow.get_draft(ALICE, draft.draft_id).version == 1


def test_a_confirmation_records_the_door_it_came_through(parts: Parts) -> None:
    """H9: cli or web, never mcp."""
    draft = parts.workflow.prepare(ALICE, "新增用户有多少？", request_id="r")
    draft = parts.workflow.amend(
        ALICE,
        draft.draft_id,
        expected_version=1,
        rules=(Rule("variant", "registered", RuleSource.USER),),
    )
    confirmation = parts.workflow.confirm(
        ALICE_WEB, draft.draft_id, version=2, definition_hash=draft.definition_hash
    )
    assert parts.store.get_confirmation("alice", confirmation.confirmation_id).channel is (
        Channel.WEB
    )


# ------------------------------------------------------------ tool errors


def test_a_stale_version_is_reported_to_the_agent_not_raised(parts: Parts) -> None:
    prepared = _prepared(parts)
    reply = _result(
        parts.call(
            "amend_query",
            {"draft_id": prepared["draft_id"], "expected_version": 9, "variant": "registered"},
        )
    )
    assert reply["isError"] is True
    assert "version" in reply["content"][0]["text"]


def test_an_unknown_reading_lists_the_real_ones(parts: Parts) -> None:
    prepared = _prepared(parts)
    reply = _result(
        parts.call(
            "amend_query",
            {"draft_id": prepared["draft_id"], "expected_version": 1, "variant": "whatever"},
        )
    )
    assert reply["isError"] is True
    assert "registered" in reply["content"][0]["text"]


def test_a_wrongly_typed_argument_is_named(parts: Parts) -> None:
    reply = _result(parts.call("amend_query", {"draft_id": "d", "expected_version": "1"}))
    assert reply["isError"] is True
    assert "expected_version" in reply["content"][0]["text"]


def test_list_metrics_names_the_readings(parts: Parts) -> None:
    listed = _result(parts.call("list_metrics"))["structuredContent"]
    assert [v["key"] for v in listed["metrics"][0]["variants"]] == ["registered", "first_order"]


def test_prepare_says_the_next_step_is_the_persons(parts: Parts) -> None:
    prepared = _prepared(parts)
    assert prepared["status"] == DraftProgress.NEEDS_INPUT.value
    assert "amend_query" in prepared["next_step"]
    amended = _result(
        parts.call(
            "amend_query",
            {"draft_id": prepared["draft_id"], "expected_version": 1, "variant": "registered"},
        )
    )["structuredContent"]
    assert amended["status"] == DraftProgress.AWAITING_CONFIRMATION.value
    assert "你不能替用户确认" in amended["next_step"]


def test_tools_refuse_an_actor_that_is_not_on_the_agent_channel(parts: Parts) -> None:
    with pytest.raises(ValueError, match="Channel.MCP"):
        QueryTools(parts.wiring, ALICE)


# -------------------------------------------------------------- protocol


def _server() -> McpServer:
    return McpServer((), name="t", version="0")


def test_initialize_answers_with_the_one_supported_revision() -> None:
    reply = _server().handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2099-01-01", "capabilities": {}, "clientInfo": {}},
        }
    )
    assert reply is not None
    assert reply["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert reply["result"]["capabilities"] == {"tools": {"listChanged": False}}


def test_notifications_get_no_reply() -> None:
    server = _server()
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/cancelled"}) is None


def test_ping_unknown_methods_and_bad_frames() -> None:
    server = _server()
    assert server.handle({"jsonrpc": "2.0", "id": "a", "method": "ping"}) == {
        "jsonrpc": "2.0",
        "id": "a",
        "result": {},
    }
    unknown = server.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
    assert unknown is not None and unknown["error"]["code"] == METHOD_NOT_FOUND
    assert server.handle_line(b"{not json")["error"]["code"] == -32700  # type: ignore[index]
    batch = server.handle_line(b'[{"jsonrpc":"2.0","id":1,"method":"ping"}]')
    assert batch is not None and batch["error"]["code"] == -32600
    no_version = server.handle({"id": 3, "method": "ping"})
    assert no_version is not None and no_version["error"]["code"] == -32600
    bool_id = server.handle({"jsonrpc": "2.0", "id": True, "method": "ping"})
    assert bool_id is not None and bool_id["error"]["code"] == -32600


# ------------------------------------------------------------ H5: stdout


def test_stdout_carries_protocol_frames_and_nothing_else(tmp_path: Path) -> None:
    """H5: a real `queryagent mcp` process, a whole session, every stdout line a JSON-RPC frame."""
    Parts(tmp_path)  # writes shop.db, metrics.yaml, mappings.yaml
    config = tmp_path / "config.yaml"
    config.write_text(
        "llm:\n  backend: openai_compatible\n  model: m\n  base_url: https://example.invalid\n"
        f"database:\n  type: sqlite\n  path: {tmp_path / 'shop.db'}\n"
        f"metrics_path: {tmp_path / 'metrics.yaml'}\n"
        f"workflow:\n  mappings_path: {tmp_path / 'mappings.yaml'}\n"
        f"  state_path: {tmp_path / 'cli-state.db'}\n"
        "trace: false\n",
        encoding="utf-8",
    )
    frames = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "prepare_query", "arguments": {"question": "新增用户有多少？"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "execute_query", "arguments": {"draft_id": "nope"}}},
    ]
    stdin = "\n".join(json.dumps(frame, ensure_ascii=False) for frame in frames) + "\n"
    completed = subprocess.run(
        [sys.executable, "-m", "queryagent.cli", "mcp", "--config", str(config),
         "--subject", "alice", "--workspace", "ops"],
        input=stdin.encode("utf-8"),
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8")
    lines = completed.stdout.decode("utf-8").splitlines()
    replies = [json.loads(line) for line in lines]
    assert [reply["id"] for reply in replies] == [1, 2, 3, 4]
    assert all(reply["jsonrpc"] == "2.0" for reply in replies)
    assert replies[2]["result"]["isError"] is False
    assert replies[3]["result"]["isError"] is True
    assert "[mcp]" in completed.stderr.decode("utf-8")
