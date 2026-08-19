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
