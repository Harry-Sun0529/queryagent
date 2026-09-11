"""QueryAgent — business numbers a person confirms before anything runs.

Two surfaces, frozen at 1.0 (ADR-014), and nothing else is promised:

- **The confirmed flow**: ``build_workflow`` / ``QueryWorkflow`` prepare a
  口径, take a person's confirmation of one exact version, and run the
  maintainer's mapping for it. For embedders — a web backend, a bot, a
  notebook — the same object the CLI, the confirmation page and the MCP
  server use.
- **The agent loop**: ``run_agent`` and the events its stream yields, for
  exploratory questions (``ask`` / ``chat``).

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
from queryagent.budget import BudgetExceeded
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
from queryagent.workflow.answers import Answers, answer_rules
from queryagent.workflow.errors import (
    ConfirmationRequired,
    MappingNotFound,
    NotFound,
    PermissionDenied,
    StaleVersion,
    WorkflowError,
    WorkflowStateError,
)
from queryagent.workflow.models import (
    ActorContext,
    BusinessDefinition,
    Candidate,
    Channel,
    Confirmation,
    DefinitionDraft,
    DraftProgress,
    DraftStatus,
    QueryRun,
    Rule,
    RuleSource,
    RunStatus,
)
from queryagent.workflow.render import render_draft, render_result
from queryagent.workflow.service import QueryWorkflow
from queryagent.workflow.wiring import WorkflowWiring, build_workflow

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
    # the confirmed flow
    "ActorContext",
    "Answers",
    "BusinessDefinition",
    "Candidate",
    "Channel",
    "Confirmation",
    "DefinitionDraft",
    "DraftProgress",
    "DraftStatus",
    "QueryRun",
    "QueryWorkflow",
    "Rule",
    "RuleSource",
    "RunStatus",
    "WorkflowWiring",
    "answer_rules",
    "build_workflow",
    "render_draft",
    "render_result",
    # errors
    "BudgetExceeded",
    "ConfirmationRequired",
    "ConnectorError",
    "LLMParseError",
    "MappingNotFound",
    "NotFound",
    "PermissionDenied",
    "QueryAgentError",
    "QueryError",
    "SafetyViolation",
    "StaleVersion",
    "ToolValidationError",
    "WorkflowError",
    "WorkflowStateError",
    "__version__",
]
