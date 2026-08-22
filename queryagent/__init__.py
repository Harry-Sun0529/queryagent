"""QueryAgent — zero-infrastructure Text-to-SQL agent library.

The public surface is deliberately small: the agent loop, the event types
its stream yields, the wiring pieces needed to build one, and the exception
hierarchy. Everything else is an implementation detail that may move.

    from queryagent import ContextBuilder, ToolRegistry, run_agent
    from queryagent.connectors.sqlite import SQLiteConnector
    from queryagent.llm import make_backend
    from queryagent.schema import render_schema
    from queryagent.tools import make_default_tools

    connector = SQLiteConnector(path="demo_shop.db")
    builder = ContextBuilder(
        schema_text=render_schema(connector.get_schema()), dialect=connector.dialect
    )
    registry = ToolRegistry(make_default_tools(connector, timeout_s=10, max_rows=200))
    for event in run_agent("有多少用户？", backend=backend, registry=registry,
                           context_builder=builder):
        ...  # every consumer is just a reader of this stream
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from queryagent.agent import run_agent
from queryagent.config import AppConfig, load_config
from queryagent.connectors import make_connector
from queryagent.context import ContextBuilder
from queryagent.errors import (
    ConnectorError,
    LLMParseError,
    QueryAgentError,
    QueryError,
    SafetyViolation,
    ToolValidationError,
)
from queryagent.events import (
    AgentEvent,
    AnswerEvent,
    ClarifyEvent,
    ErrorEvent,
    ObservationEvent,
    RetryEvent,
    ThinkEvent,
    ToolCallEvent,
    UsageEvent,
)
from queryagent.llm import make_backend
from queryagent.metrics.yaml_store import YamlMetricStore
from queryagent.tools import ToolRegistry, make_clarify_tool, make_default_tools

try:  # single source of truth: whatever pip actually installed
    __version__ = _version("queryagent")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0+unknown"

__all__ = [
    # agent
    "run_agent",
    # events
    "AgentEvent",
    "AnswerEvent",
    "ClarifyEvent",
    "ErrorEvent",
    "ObservationEvent",
    "RetryEvent",
    "ThinkEvent",
    "ToolCallEvent",
    "UsageEvent",
    # wiring
    "AppConfig",
    "ContextBuilder",
    "ToolRegistry",
    "YamlMetricStore",
    "load_config",
    "make_backend",
    "make_clarify_tool",
    "make_connector",
    "make_default_tools",
    # errors
    "ConnectorError",
    "LLMParseError",
    "QueryAgentError",
    "QueryError",
    "SafetyViolation",
    "ToolValidationError",
    "__version__",
]
