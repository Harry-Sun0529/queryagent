"""A stdio MCP server, hand-written (P01, ADR-013).

JSON-RPC 2.0, one message per line on stdin and on stdout, one protocol
version, four methods: ``initialize``, ``ping``, ``tools/list`` and
``tools/call``. Notifications get no reply. Written by hand for the reason
the OpenAI-compatible backend is: the protocol is small, a dependency would
be larger than it, and a server whose every frame is in one file can be
explained frame by frame.

stdout carries protocol frames and nothing else (H5). While the server runs,
``sys.stdout`` points at stderr, so a stray ``print`` anywhere below lands
where a person reads it instead of corrupting the stream a host parses.

This module knows nothing about queries. Tools are handed in; what they may
do is decided by which tools exist, and a confirmation tool does not.
"""

from __future__ import annotations

import contextlib
import json
import sys
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, BinaryIO

from queryagent.errors import QueryAgentError

PROTOCOL_VERSION = "2025-06-18"
"""The one revision implemented. A host asking for another is answered with
this one, which the specification lets it accept or decline."""

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


class ToolArgumentError(ValueError):
    """A tool was called with arguments it does not take. Reported to the agent to correct."""


@dataclass(frozen=True)
class ToolResult:
    """What a tool says back: text for any host, structure for hosts that read it."""

    text: str
    structured: Mapping[str, Any] | None = None
    is_error: bool = False


@dataclass(frozen=True)
class Tool:
    """One tool: its advertised shape, and the function behind it."""

    name: str
    title: str
    description: str
    input_schema: Mapping[str, Any]
    handler: Callable[[dict[str, Any]], ToolResult]
    annotations: Mapping[str, Any] = field(default_factory=dict)

    def listing(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
        }
        if self.annotations:
            entry["annotations"] = dict(self.annotations)
        return entry


class McpServer:
    """Dispatches JSON-RPC messages to a fixed table of tools."""

    def __init__(
        self,
        tools: Sequence[Tool],
        *,
        name: str,
        version: str,
        instructions: str = "",
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._tools = {tool.name: tool for tool in tools}
        self._name = name
        self._version = version
        self._instructions = instructions
        self._log = log or (lambda text: print(text, file=sys.stderr))

    def serve(self, stdin: BinaryIO, stdout: BinaryIO) -> int:
        """Answer messages from ``stdin`` until it closes. Returns the exit code."""
        with contextlib.redirect_stdout(sys.stderr):
            for raw in stdin:
                line = raw.strip()
                if not line:
                    continue
                reply = self.handle_line(line)
                if reply is not None:
                    stdout.write(encode(reply))
                    stdout.flush()
        return 0

    def handle_line(self, line: bytes | str) -> dict[str, Any] | None:
        """One line in, one reply out, or None for a notification."""
        try:
            message = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error(None, PARSE_ERROR, "Parse error")
        if isinstance(message, list):
            # Batches were removed from the protocol in this revision.
            return _error(None, INVALID_REQUEST, "Batching is not supported")
        return self.handle(message)

    def handle(self, message: Any) -> dict[str, Any] | None:
        """Dispatch one decoded message."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _error(_id_of(message), INVALID_REQUEST, "Invalid Request")
        method = message.get("method")
        if not isinstance(method, str):
            if "result" in message or "error" in message:
                return None  # a response to a request this server never sends
            return _error(_id_of(message), INVALID_REQUEST, "Invalid Request")
        if "id" not in message:
            return None  # notifications/initialized, notifications/cancelled, ...
        request_id = message["id"]
        if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
            return _error(None, INVALID_REQUEST, "Request id must be a string or an integer")
        params = message.get("params", {})
        if not isinstance(params, dict):
            return _error(request_id, INVALID_PARAMS, "params must be an object")
        if method == "initialize":
            return _result(request_id, self._initialize())
        if method == "ping":
            return _result(request_id, {})
        if method == "tools/list":
            return _result(request_id, {"tools": [tool.listing() for tool in self._tools.values()]})
        if method == "tools/call":
            return self._call(request_id, params)
        return _error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def _initialize(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self._name, "version": self._version},
        }
        if self._instructions:
            result["instructions"] = self._instructions
        return result

    def _call(self, request_id: str | int, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            return _error(request_id, INVALID_PARAMS, f"Unknown tool: {name}")
        arguments = params.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return _error(request_id, INVALID_PARAMS, "arguments must be an object")
        try:
            outcome = tool.handler(arguments)
        except (ValueError, QueryAgentError) as exc:
            # A refusal is an answer the agent should read and act on, not a
            # protocol failure: it goes back as a tool result (isError).
            outcome = ToolResult(text=str(exc), is_error=True)
        except Exception as exc:  # noqa: BLE001 - one bad call must not end the session
            self._log(traceback.format_exc())
            outcome = ToolResult(
                text=f"QueryAgent 内部错误（缺陷，不是你的调用有误）：{type(exc).__name__}: {exc}",
                is_error=True,
            )
        return _result(request_id, _tool_payload(outcome))


def _tool_payload(outcome: ToolResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "content": [{"type": "text", "text": outcome.text}],
        "isError": outcome.is_error,
    }
    if outcome.structured is not None:
        payload["structuredContent"] = dict(outcome.structured)
    return payload


def _id_of(message: Any) -> str | int | None:
    if isinstance(message, dict):
        candidate = message.get("id")
        if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
            return candidate
    return None


def _result(request_id: str | int, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: str | int | None, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def encode(message: Mapping[str, Any]) -> bytes:
    """One frame: compact JSON on one line. ``json`` escapes newlines inside strings."""
    return (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
