"""v1.0 T48: the frozen surfaces, snapshotted (ADR-014, H12).

Each snapshot is regenerated from the code and compared with the file under
tests/contract/. After an intended change, regenerate them with

    QUERYAGENT_UPDATE_CONTRACT=1 pytest tests/test_public_contract.py

and put the digest the last test asks for in the newest CHANGELOG section:
changing a frozen surface means telling the people who rely on it.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import hashlib
import json
import os
import re
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import queryagent
from queryagent import cli
from queryagent.config import AppConfig
from queryagent.mcp.tools import input_schemas
from queryagent.metrics.yaml_store import METRIC_KEYS, VARIANT_KEYS
from queryagent.workflow.mappings import DIMENSION_KEYS, MAPPING_KEYS
from queryagent.workflow.models import ALLOWED_RULE_KEYS, REQUIRABLE_RULE_KEYS
from tests.wired import Parts

CONTRACT = Path(__file__).parent / "contract"
CHANGELOG = Path(__file__).parent.parent / "CHANGELOG.md"
UPDATE = os.environ.get("QUERYAGENT_UPDATE_CONTRACT") == "1"


def _cli() -> dict[str, Any]:
    parser = cli.build_parser()
    subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    commands: dict[str, Any] = {}
    for name, command in sorted(subparsers.choices.items()):
        commands[name] = [
            {
                "dest": action.dest,
                "flags": list(action.option_strings),
                "kind": type(action).__name__,
                "required": bool(action.required) or not action.option_strings,
                "choices": list(action.choices) if action.choices else None,
                "default": _default(action),
            }
            for action in command._actions
            if not isinstance(action, argparse._HelpAction)
        ]
    return commands


def _default(action: argparse.Action) -> Any:
    if action.dest == "subject":
        return "<the local user>"  # $USER: differs per machine, frozen as a rule
    value = action.default
    return value if isinstance(value, (str, int, float, bool, list, type(None))) else repr(value)


def _exit_codes() -> dict[str, int]:
    return {
        "ok": cli.EXIT_OK,
        "refused_declined_or_misconfigured": cli.EXIT_USER_ERROR,
        "eval_cases_failed": cli.EXIT_EVAL_FAILED,
        "defect": cli.EXIT_INTERNAL_DEFECT,
        "retry_later": cli.EXIT_TEMPORARY_FAILURE,
        "interrupted": cli.EXIT_INTERRUPTED,
    }


def _keys(cls: type) -> dict[str, Any]:
    """A config dataclass as the YAML keys it reads: nested sections nested."""
    hints = typing.get_type_hints(cls)
    return {f.name: _section(hints[f.name]) for f in dataclasses.fields(cls)}


def _section(hint: Any) -> Any:
    if dataclasses.is_dataclass(hint) and isinstance(hint, type):
        return _keys(hint)
    for argument in typing.get_args(hint):
        nested = _section(argument)
        if nested is not None:
            return nested
    return None


def _config() -> dict[str, Any]:
    return _keys(AppConfig)


def _files() -> dict[str, Any]:
    return {
        "metrics.yaml": {
            "metric": list(METRIC_KEYS),
            "variant": list(VARIANT_KEYS),
            "required_rules": list(REQUIRABLE_RULE_KEYS),
        },
        "query_mappings.yaml": {
            "mapping": list(MAPPING_KEYS),
            "freshness": ["lag_days"],
            "enforces": list(ALLOWED_RULE_KEYS),
            "dimension": list(DIMENSION_KEYS),
        },
    }


def _public_api() -> list[str]:
    return sorted(queryagent.__all__)


SNAPSHOTS: dict[str, Callable[[], Any]] = {
    "cli.json": _cli,
    "config.json": _config,
    "exit_codes.json": _exit_codes,
    "files.json": _files,
    "mcp_tools.json": input_schemas,
    "public_api.json": _public_api,
}


def _render(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _digest() -> str:
    digest = hashlib.sha256()
    for name in sorted(SNAPSHOTS):
        digest.update(name.encode())
        digest.update(_render(SNAPSHOTS[name]()).encode("utf-8"))
    return digest.hexdigest()[:12]


@pytest.mark.parametrize("name", sorted(SNAPSHOTS))
def test_the_frozen_surface_matches_its_snapshot(name: str) -> None:
    current = _render(SNAPSHOTS[name]())
    path = CONTRACT / name
    if UPDATE:
        CONTRACT.mkdir(exist_ok=True)
        path.write_text(current, encoding="utf-8")
        return
    assert path.exists(), f"no snapshot {path}: generate it with QUERYAGENT_UPDATE_CONTRACT=1"
    recorded = path.read_text(encoding="utf-8")
    difference = "".join(
        difflib.unified_diff(
            recorded.splitlines(keepends=True), current.splitlines(keepends=True), name, "now"
        )
    )
    assert current == recorded, (
        f"a frozen surface changed ({name}). If that is intended, regenerate with "
        "QUERYAGENT_UPDATE_CONTRACT=1 pytest tests/test_public_contract.py and record the "
        f"change and the new digest in CHANGELOG.md (ADR-014).\n{difference}"
    )


def test_the_newest_changelog_section_records_the_contract_digest() -> None:
    """H12: a snapshot can be regenerated in one command; the CHANGELOG line is the
    part that makes someone say, where users read it, that the contract moved."""
    wanted = f"契约摘要：{_digest()}"
    sections = re.split(r"^## \[", CHANGELOG.read_text(encoding="utf-8"), flags=re.M)[1:]
    # An empty [Unreleased] heading holds nothing yet; the newest entry is below it.
    if sections and sections[0].startswith("Unreleased]") and not sections[0][12:].strip():
        sections = sections[1:]
    newest = sections[0] if sections else ""
    assert wanted in newest, f"add this line to the newest section of CHANGELOG.md: {wanted}"


def test_tools_list_reports_exactly_the_frozen_schemas(tmp_path: Path) -> None:
    parts = Parts(tmp_path)
    reply = parts.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert reply is not None
    listed = {tool["name"]: tool["inputSchema"] for tool in reply["result"]["tools"]}
    assert listed == input_schemas()
    parts.close()


def test_every_name_in_all_is_importable() -> None:
    for name in queryagent.__all__:
        assert hasattr(queryagent, name), name


def test_the_workflow_is_usable_from_the_package_alone(tmp_path: Path) -> None:
    """The library surface: an embedder confirms and runs without importing internals."""
    from queryagent import ActorContext, Channel, DraftProgress, Rule, RuleSource

    parts = Parts(tmp_path)
    person = ActorContext("alice", "ops", channel=Channel.WEB)
    draft = parts.workflow.prepare(person, "新增用户有多少？", request_id="r")
    draft = parts.workflow.amend(
        person, draft.draft_id, expected_version=1,
        rules=(Rule("variant", "registered", RuleSource.USER),),
    )
    parts.workflow.confirm(
        person, draft.draft_id, version=draft.version, definition_hash=draft.definition_hash
    )
    run = parts.workflow.execute_confirmed(person, draft.draft_id)
    assert run.rows == ((3,),)
    assert parts.workflow.progress(person, draft.draft_id) is DraftProgress.EXECUTED
    parts.close()
