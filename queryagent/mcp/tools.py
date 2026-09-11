"""The five tools an agent gets, and the one it does not (T44, ADR-013).

``list_metrics``, ``prepare_query``, ``amend_query``, ``query_status`` and
``execute_query``. There is no ``confirm_query``. An agent that decides to
confirm on its user's behalf finds nothing to call: the gate is not a rule
the agent is asked to follow, it is an operation the agent cannot express.

``execute_query`` names a draft. The service looks for a confirmation a
person gave its current version, in the terminal or on the confirmation
page, and without one runs nothing (H3). What an agent fills in is marked
「Agent 代填」 on the sheet the person confirms, so an agent's guess never
reads as the person's own choice (P05).

Identity comes from the command that started the server (P02). No tool takes
a subject or a workspace, and an argument no tool takes is refused rather
than ignored: an agent that believes it can name an identity should hear
that it cannot.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from queryagent import __version__
from queryagent.mcp.server import McpServer, Tool, ToolArgumentError, ToolResult
from queryagent.workflow.answers import Answers, answer_rules
from queryagent.workflow.models import (
    VARIANT_RULE_KEY,
    ActorContext,
    Channel,
    DefinitionDraft,
    DraftProgress,
    QueryRun,
    RunStatus,
)
from queryagent.workflow.render import render_result, rule_label, rule_text, source_label
from queryagent.workflow.wiring import WorkflowWiring

INSTRUCTIONS = (
    "QueryAgent 按维护者声明、并经用户本人确认的口径查询业务数据。流程："
    "prepare_query(问题) → 把返回的确认单原样给用户看 → 有未定项时问用户，再用 amend_query 补上"
    "（你补的值在确认单上标为「Agent 代填」）→ 请用户在本地确认页（queryagent web）或终端"
    "（queryagent confirm <草案号>）确认 → execute_query(draft_id)。"
    "你不能确认，也没有确认工具；没有人的确认，execute_query 不会执行任何查询。"
)

_DRAFT_ID = {"type": "string", "description": "prepare_query 返回的完整 draft_id"}

_SCHEMAS: dict[str, dict[str, Any]] = {
    "list_metrics": {"type": "object", "properties": {}, "additionalProperties": False},
    "prepare_query": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "用户的业务问题，原话即可"},
        },
        "required": ["question"],
        "additionalProperties": False,
    },
    "amend_query": {
        "type": "object",
        "properties": {
            "draft_id": _DRAFT_ID,
            "expected_version": {
                "type": "integer",
                "minimum": 1,
                "description": "你看到的确认单版本；草案已被改过时会被拒绝",
            },
            "variant": {"type": "string", "description": "选定口径，取 candidates 里的 key"},
            "adopt": {
                "type": "array",
                "items": {"type": "string"},
                "description": "文档分歧时采用的写法，取 candidates 里形如 counting_basis:0 的 key",
            },
            "period": {
                "type": "string",
                "description": "统计区间，如 上个月、2026-08-01..2026-08-31",
            },
            "group_by": {"type": "string", "description": "day / week / month / 维度名 / none"},
            "filter": {
                "type": "string",
                "description": "只统计一个声明过的取值，如 渠道=广告；none 表示不过滤",
            },
            "rules": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "维护者要求写明、但还没有来源的规则，键取 missing 里的 key",
            },
        },
        "required": ["draft_id", "expected_version"],
        "additionalProperties": False,
    },
    "query_status": {
        "type": "object",
        "properties": {"draft_id": _DRAFT_ID},
        "required": ["draft_id"],
        "additionalProperties": False,
    },
    "execute_query": {
        "type": "object",
        "properties": {"draft_id": _DRAFT_ID},
        "required": ["draft_id"],
        "additionalProperties": False,
    },
}


def make_server(wiring: WorkflowWiring, actor: ActorContext) -> McpServer:
    """The MCP server for one person's agent."""
    return McpServer(
        QueryTools(wiring, actor).table(),
        name="queryagent",
        version=__version__,
        instructions=INSTRUCTIONS,
    )


class QueryTools:
    """The tool handlers, bound to one wired workflow and one identity."""

    def __init__(self, wiring: WorkflowWiring, actor: ActorContext) -> None:
        if actor.channel is not Channel.MCP:
            # The channel is what marks the agent's rules as its own and keeps
            # it from confirming. An MCP door acting under a human channel
            # would quietly undo both.
            raise ValueError("MCP tools act for an agent: build the actor with Channel.MCP")
        self._wiring = wiring
        self._workflow = wiring.workflow
        self._actor = actor

    def table(self) -> tuple[Tool, ...]:
        return (
            Tool(
                "list_metrics",
                "列出可查询的指标",
                "列出维护者声明的业务指标、各自可选的口径，以及可用于分组或过滤的维度与取值。",
                _SCHEMAS["list_metrics"],
                self.list_metrics,
                {"readOnlyHint": True, "openWorldHint": False},
            ),
            Tool(
                "prepare_query",
                "生成口径确认单",
                "把一个业务问题变成待确认的口径草案，返回确认单。不执行任何查询。"
                "请把确认单原样给用户看。",
                _SCHEMAS["prepare_query"],
                self.prepare_query,
                {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
            ),
            Tool(
                "amend_query",
                "补充口径",
                "为草案补上未定项（口径、文档取法、区间、分组、过滤、缺口规则）。"
                "你补的值标为「Agent 代填」，用户确认时会看到。每次补充产生新版本。",
                _SCHEMAS["amend_query"],
                self.amend_query,
                {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
            ),
            Tool(
                "query_status",
                "查看草案状态",
                "查看草案是否还缺信息、是否已由用户确认、是否已执行。",
                _SCHEMAS["query_status"],
                self.query_status,
                {"readOnlyHint": True, "openWorldHint": False},
            ),
            Tool(
                "execute_query",
                "执行已确认的口径",
                "执行用户本人已确认的草案当前版本，返回结果。用户没有确认时不执行任何查询。"
                "一次确认只执行一次；再次调用返回同一次的结果。",
                _SCHEMAS["execute_query"],
                self.execute_query,
                {
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            ),
        )

    # ------------------------------------------------------------- handlers

    def list_metrics(self, arguments: dict[str, Any]) -> ToolResult:
        _check(arguments, "list_metrics")
        metrics = [
            {
                "name": metric.name,
                "display_name": metric.display_name,
                "definition": metric.definition,
                "variants": [
                    {"key": v.key, "label": v.label, "definition": v.definition}
                    for v in metric.variants
                ],
            }
            for metric in self._wiring.metrics.all()
        ]
        dimensions = [
            {
                "key": dimension.key,
                "label": dimension.label,
                "values": [stored for stored, _words in dimension.values],
            }
            for dimension in self._wiring.dimensions
        ]
        lines = [
            f"{m['display_name'] or m['name']}（{m['name']}）：{m['definition']}" for m in metrics
        ]
        return ToolResult(
            text="\n".join(lines) or "（维护者尚未声明任何指标）",
            structured={"metrics": metrics, "dimensions": dimensions},
        )

    def prepare_query(self, arguments: dict[str, Any]) -> ToolResult:
        question = _check(arguments, "prepare_query")["question"].strip()
        if not question:
            raise ToolArgumentError("question 不能为空")
        draft = self._workflow.prepare(self._actor, question, request_id=uuid.uuid4().hex)
        return self._draft_view(draft)

    def amend_query(self, arguments: dict[str, Any]) -> ToolResult:
        args = _check(arguments, "amend_query")
        draft = self._workflow.get_draft(self._actor, args["draft_id"])
        answers = Answers(
            variant=args.get("variant", ""),
            adopt=tuple(args.get("adopt", ())),
            rules=tuple(args.get("rules", {}).items()),
            period=args.get("period", ""),
            group_by=args.get("group_by", ""),
            value_filter=args.get("filter", ""),
        )
        rules = answer_rules(
            draft.definition,
            answers,
            source=self._actor.authoring_source,
            today=self._wiring.today(),
            dimensions=self._wiring.dimensions,
        )
        updated = self._workflow.amend(
            self._actor, draft.draft_id, expected_version=args["expected_version"], rules=rules
        )
        return self._draft_view(updated)

    def query_status(self, arguments: dict[str, Any]) -> ToolResult:
        draft_id = _check(arguments, "query_status")["draft_id"]
        return self._draft_view(self._workflow.get_draft(self._actor, draft_id))

    def execute_query(self, arguments: dict[str, Any]) -> ToolResult:
        draft_id = _check(arguments, "execute_query")["draft_id"]
        run = self._workflow.execute_confirmed(self._actor, draft_id)
        draft = self._workflow.get_draft(self._actor, draft_id)
        if run.status is RunStatus.EXECUTING:
            return ToolResult(
                text="这次确认的查询正在执行，稍后用 query_status 查看。", is_error=True
            )
        if run.status is RunStatus.FAILED:
            return ToolResult(
                text=f"执行失败：{run.error}。一次确认只执行一次；要重试，请用户重新确认。",
                is_error=True,
            )
        lines = render_result(draft.definition, run, self._wiring.labels)
        return ToolResult(text="\n".join(lines), structured=_run_view(draft, run, lines))

    # --------------------------------------------------------------- views

    def _draft_view(self, draft: DefinitionDraft) -> ToolResult:
        definition = draft.definition
        progress = self._workflow.progress(self._actor, draft.draft_id)
        sheet = self._wiring.sheet(self._actor, draft)
        freshness = self._workflow.freshness_advisory(self._actor, draft.draft_id)
        hint = _next_step(draft, progress)
        structured = {
            "draft_id": draft.draft_id,
            "version": draft.version,
            "status": progress.value,
            "definition_hash": draft.definition_hash,
            "sheet": sheet,
            "freshness": list(freshness),
            "rules": [
                {
                    "key": rule.key,
                    "label": rule_label(rule.key),
                    "value": rule_text(definition, rule, self._wiring.labels),
                    "source": rule.source.value,
                    "source_label": source_label(rule.source),
                }
                for rule in definition.rules
            ],
            "missing": [{"key": key, "label": rule_label(key)} for key in definition.missing],
            "candidates": [
                {
                    "key": c.key,
                    "label": c.label,
                    "summary": c.summary,
                    "answers": "variant" if c.rule_key == VARIANT_RULE_KEY else "adopt",
                }
                for c in definition.candidates
            ],
            "next_step": hint,
        }
        text = sheet
        if freshness:
            text += "\n\n数据新鲜度（确认前的参考，不属于口径）：\n" + "\n".join(
                f"  · {note}" for note in freshness
            )
        text += f"\n\n状态：{progress.value}（draft_id={draft.draft_id}，version={draft.version}）"
        text += f"\n下一步：{hint}"
        return ToolResult(text=text, structured=structured)


def _next_step(draft: DefinitionDraft, progress: DraftProgress) -> str:
    short = draft.draft_id[:8]
    if progress is DraftProgress.NEEDS_INPUT:
        missing = "、".join(rule_label(key) for key in draft.definition.missing)
        return (
            f"口径还有未定项：{missing}。请把确认单给用户看，问清楚后用 amend_query 补上"
            f"（expected_version={draft.version}）；你补的值会标为「Agent 代填」。"
        )
    if progress is DraftProgress.AWAITING_CONFIRMATION:
        return (
            "口径已完整，但还没有人确认。请把确认单原样给用户看，请用户在本地确认页"
            f"（queryagent web）或终端运行 `queryagent confirm {short}` 确认；你不能替用户确认。"
            "用户确认后再调用 execute_query。"
        )
    if progress is DraftProgress.CONFIRMED:
        return "用户已确认当前版本，可以调用 execute_query。"
    if progress is DraftProgress.EXECUTED:
        return "已执行；再次调用 execute_query 会返回同一次的结果。"
    return "草案已失效（所依据的文档已变化）；请重新调用 prepare_query。"


def _run_view(draft: DefinitionDraft, run: QueryRun, lines: list[str]) -> dict[str, Any]:
    return {
        "draft_id": draft.draft_id,
        "version": draft.version,
        "status": DraftProgress.EXECUTED.value,
        "columns": list(run.columns),
        "rows": [[_json_value(value) for value in row] for row in run.rows],
        "truncated": run.truncated,
        "sql": run.sql,
        "params": list(run.params),
        "data_through": run.data_through,
        "freshness_sql": run.freshness_sql,
        "report": "\n".join(lines),
    }


def _json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _check(arguments: Mapping[str, Any], tool: str) -> dict[str, Any]:
    """Arguments that match the tool's schema, or ToolArgumentError saying what is wrong.

    Hand-checked against the same schema the host was shown, so the two
    cannot drift. Unknown names are refused, identity names included (H2).
    """
    schema = _SCHEMAS[tool]
    properties: dict[str, Any] = schema["properties"]
    unknown = sorted(set(arguments) - set(properties))
    if unknown:
        allowed = "、".join(properties) or "（无）"
        raise ToolArgumentError(
            f"{tool} 不接受参数：{', '.join(unknown)}；可用参数：{allowed}。"
            "身份（subject / workspace）只来自启动 queryagent mcp 的命令，不能由工具参数指定。"
        )
    missing = [name for name in schema.get("required", ()) if name not in arguments]
    if missing:
        raise ToolArgumentError(f"{tool} 缺少参数：{', '.join(missing)}")
    for name, value in arguments.items():
        _check_type(tool, name, value, properties[name])
    return dict(arguments)


def _check_type(tool: str, name: str, value: Any, spec: Mapping[str, Any]) -> None:
    kind = spec.get("type")
    if kind == "string":
        ok = isinstance(value, str)
    elif kind == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
        ok = ok and value >= spec.get("minimum", value)
    elif kind == "array":
        ok = isinstance(value, list) and all(isinstance(item, str) for item in value)
    elif kind == "object":
        ok = isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in value.items()
        )
    else:  # pragma: no cover - every schema above names a type
        ok = False
    if not ok:
        raise ToolArgumentError(f"{tool} 的参数 {name} 应为 {kind}")
