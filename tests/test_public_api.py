"""The package's public surface.

README calls this a library and contrasts it with WrenAI's platform, so
`import queryagent` has to give you something to work with. These tests are
that promise, written down.
"""

from __future__ import annotations

from pathlib import Path


def test_the_agent_loop_and_events_are_importable_from_the_package() -> None:
    from queryagent import AnswerEvent, ClarifyEvent, ToolCallEvent, run_agent

    assert callable(run_agent)
    assert AnswerEvent(text="x").text == "x"
    assert ClarifyEvent(question="?", conflicting_metrics=()).question == "?"
    assert ToolCallEvent(tool_name="t", arguments={}, tool_call_id="1").tool_name == "t"


def test_wiring_pieces_are_importable_from_the_package() -> None:
    from queryagent import (
        ContextBuilder,
        ToolRegistry,
        load_config,
        make_backend,
        make_connector,
        make_default_tools,
    )

    for obj in (
        ContextBuilder,
        ToolRegistry,
        load_config,
        make_backend,
        make_connector,
        make_default_tools,
    ):
        assert callable(obj)


def test_error_hierarchy_is_importable() -> None:
    from queryagent import ConnectorError, QueryAgentError, SafetyViolation

    assert issubclass(SafetyViolation, QueryAgentError)
    assert issubclass(ConnectorError, QueryAgentError)


def test_star_import_exposes_the_documented_surface() -> None:
    import queryagent

    assert queryagent.__all__, "a library without __all__ has no stated surface"
    for name in queryagent.__all__:
        assert hasattr(queryagent, name), f"__all__ names {name} but it is missing"


def test_the_readme_library_example_actually_runs(tmp_path: Path) -> None:
    """The snippet README shows must be executable, not aspirational —
    documented code that was never run is how a library's first impression
    breaks."""
    import sqlite3

    from queryagent import AnswerEvent, ContextBuilder, ToolRegistry, run_agent
    from queryagent.connectors.sqlite import SQLiteConnector
    from queryagent.llm.base import ModelResponse
    from queryagent.schema import render_schema
    from queryagent.tools import make_default_tools

    db = tmp_path / "shop.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE users (id INTEGER)")
    conn.execute("INSERT INTO users VALUES (1)")
    conn.commit()
    conn.close()

    class StubBackend:
        def complete(self, messages, tools=None, **kwargs):  # type: ignore[no-untyped-def]
            return ModelResponse(text="1 位用户", stop_reason="stop")

    connector = SQLiteConnector(path=str(db))
    builder = ContextBuilder(
        schema_text=render_schema(connector.get_schema()), dialect=connector.dialect
    )
    registry = ToolRegistry(make_default_tools(connector, timeout_s=5, max_rows=10))

    answers = [
        event.text
        for event in run_agent(
            "有多少用户？",
            backend=StubBackend(),
            registry=registry,
            context_builder=builder,
        )
        if isinstance(event, AnswerEvent)
    ]
    connector.close()
    assert answers == ["1 位用户"]
