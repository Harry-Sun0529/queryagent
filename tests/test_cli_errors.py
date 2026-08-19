"""CLI-level tests: common新手 mistakes must produce actionable messages.

These go through ``main()`` so they cover the top-level error handling the
way a user actually hits it (exit code + stderr text, no raw traceback).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from queryagent.cli import main

SQLITE_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: {db}
trace: false
"""


def write_config(tmp_path: Path, db: str = "missing.db") -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(SQLITE_CONFIG.format(db=db), encoding="utf-8")
    return path


def real_db(tmp_path: Path) -> str:
    """An actual (empty) SQLite file, so the db check passes and later
    failures — the ones under test — are the ones that surface."""
    import sqlite3

    path = tmp_path / "real.db"
    sqlite3.connect(path).close()
    return str(path)


def test_missing_api_key_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    code = main(["ask", "q", "--config", str(write_config(tmp_path, db=real_db(tmp_path)))])
    err = capsys.readouterr().err
    assert code == 2
    assert "OPENAI_API_KEY" in err
    assert "export" in err  # tells the user what to actually do
    assert "Traceback" not in err


def test_missing_config_file_is_actionable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["ask", "q", "--config", str(tmp_path / "nope.yaml")])
    err = capsys.readouterr().err
    assert code == 2
    assert "nope.yaml" in err
    assert "Traceback" not in err


def test_missing_database_file_suggests_demo_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    config = write_config(tmp_path, db=str(tmp_path / "absent.db"))
    code = main(["ask", "q", "--config", str(config)])
    err = capsys.readouterr().err
    assert code == 2
    assert "make demo-data" in err
    assert "Traceback" not in err


def test_missing_optional_driver_names_the_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    config = tmp_path / "ch.yaml"
    config.write_text(
        "llm:\n  backend: openai_compatible\n  model: m\n"
        "  base_url: https://api.deepseek.com\n"
        "database:\n  type: clickhouse\n  host: 127.0.0.1\n  database: demo\n",
        encoding="utf-8",
    )
    import sys

    # Another test may already have imported both modules; drop the connector
    # module too so make_connector's lazy import actually re-executes.
    monkeypatch.setitem(sys.modules, "clickhouse_driver", None)
    monkeypatch.delitem(sys.modules, "queryagent.connectors.clickhouse", raising=False)
    code = main(["ask", "q", "--config", str(config)])
    err = capsys.readouterr().err
    assert code == 2
    assert "clickhouse" in err.lower()
    assert "pip install" in err
    assert "Traceback" not in err


def test_invalid_config_value_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    path = tmp_path / "bad.yaml"
    path.write_text("llm:\n  backend: gemini\n  model: m\ndatabase:\n  type: sqlite\n  path: x\n",
                    encoding="utf-8")
    code = main(["ask", "q", "--config", str(path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "backend" in err
    assert "Traceback" not in err


UNREACHABLE_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: http://127.0.0.1:9
database:
  type: sqlite
  path: {db}
trace: false
"""


def test_chat_survives_a_failing_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One bad turn must not end the session — the user keeps their context."""
    config = tmp_path / "unreachable.yaml"
    config.write_text(UNREACHABLE_CONFIG.format(db=real_db(tmp_path)), encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setattr(
        "queryagent.llm.openai_backend.OpenAICompatibleBackend._post_with_retries",
        lambda self, body: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    asked = iter(["第一个问题", "第二个问题", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(asked))

    code = main(["chat", "--config", str(config)])

    err = capsys.readouterr().err
    assert code == 0  # the session itself ended normally
    assert err.count("[错误]") == 2  # both turns reported, neither killed the loop
    assert "Traceback" not in err


EVAL_CONFIG = """\
llm:
  backend: openai_compatible
  model: deepseek-v4-flash
  base_url: https://api.deepseek.com
database:
  type: sqlite
  path: {db}
trace: false
"""


def test_unopenable_database_fails_its_cases_not_the_whole_suite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A 30-case public run costs real money and minutes; one missing database
    # must not discard every result gathered so far.
    import json

    monkeypatch.setenv("OPENAI_API_KEY", "x")
    subset = tmp_path / "subset.json"
    subset.write_text(
        json.dumps(
            [
                {"id": "gone_1", "db_id": "gone", "question": "q1", "gold_sql": "SELECT 1"},
                {"id": "gone_2", "db_id": "gone", "question": "q2", "gold_sql": "SELECT 1"},
            ]
        ),
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(EVAL_CONFIG.format(db=real_db(tmp_path)), encoding="utf-8")
    report = tmp_path / "report.md"

    code = main(
        [
            "eval",
            "--config", str(config),
            "--public", str(subset),
            "--db-dir", str(tmp_path / "databases"),
            "--output", str(report),
        ]
    )

    assert code == 3  # cases failed, but the suite ran to completion
    assert report.exists(), "the report must be written even when a database is unusable"
    text = report.read_text(encoding="utf-8")
    assert "gone_1" in text and "gone_2" in text
    assert "gone" in text.lower()


def test_report_directory_is_created_if_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Losing a finished (paid-for) run because the output folder is missing
    # is the worst possible moment to fail.
    import json

    monkeypatch.setenv("OPENAI_API_KEY", "x")
    subset = tmp_path / "subset.json"
    subset.write_text(
        json.dumps([{"id": "gone_1", "db_id": "gone", "question": "q", "gold_sql": "SELECT 1"}]),
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(EVAL_CONFIG.format(db=real_db(tmp_path)), encoding="utf-8")
    report = tmp_path / "nested" / "deeper" / "report.md"

    main(
        [
            "eval",
            "--config", str(config),
            "--public", str(subset),
            "--db-dir", str(tmp_path / "databases"),
            "--output", str(report),
        ]
    )
    assert report.exists()


class RecordingBackend:
    """A backend that answers immediately and remembers being closed."""

    def __init__(self) -> None:
        self.closed = False

    def complete(self, messages, tools=None, **kwargs):  # type: ignore[no-untyped-def]
        from queryagent.llm.base import ModelResponse

        return ModelResponse(text="42", stop_reason="stop")

    def close(self) -> None:
        self.closed = True


def test_ask_releases_the_llm_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Each backend owns an httpx.Client; a public eval builds one per
    # database, so never closing them leaks a connection pool per data source.
    backend = RecordingBackend()
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setattr("queryagent.cli.make_backend", lambda _config: backend)
    config = write_config(tmp_path, db=real_db(tmp_path))

    assert main(["ask", "q", "--config", str(config)]) == 0
    assert backend.closed, "the LLM client must be released when the command ends"


def test_client_is_released_even_when_the_run_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    backend = RecordingBackend()

    def explode(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    backend.complete = explode  # type: ignore[method-assign]
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setattr("queryagent.cli.make_backend", lambda _config: backend)
    config = write_config(tmp_path, db=real_db(tmp_path))

    main(["ask", "q", "--config", str(config)])
    assert backend.closed


def test_interrupt_exits_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ctrl-C during a slow query is normal use, not a crash to report."""
    backend = RecordingBackend()

    def interrupted(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise KeyboardInterrupt

    backend.complete = interrupted  # type: ignore[method-assign]
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setattr("queryagent.cli.make_backend", lambda _config: backend)
    config = write_config(tmp_path, db=real_db(tmp_path))

    code = main(["ask", "q", "--config", str(config)])

    err = capsys.readouterr().err
    assert code == 130  # conventional exit code for SIGINT
    assert "Traceback" not in err
    assert backend.closed, "resources are released on interrupt too"
