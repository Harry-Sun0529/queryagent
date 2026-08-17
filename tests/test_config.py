"""Unit tests for config loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from queryagent.config import load_config

VALID = """\
llm:
  backend: anthropic
  model: claude-sonnet-5
database:
  type: mysql
  host: 127.0.0.1
  port: 3307
  user: ro
  password: pw
  database: demo_shop
safety:
  timeout_s: 5
  max_rows: 50
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_config_loads(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, VALID))
    assert config.llm.backend == "anthropic"
    assert config.llm.model == "claude-sonnet-5"
    assert config.database.port == 3307
    assert config.safety.timeout_s == 5
    assert config.safety.max_rows == 50
    assert config.metrics_path is None


def test_safety_defaults(tmp_path: Path) -> None:
    text = VALID.split("safety:")[0]
    config = load_config(write(tmp_path, text))
    assert config.safety.timeout_s == 10
    assert config.safety.max_rows == 200


def test_api_key_in_config_rejected(tmp_path: Path) -> None:
    text = VALID.replace("model: claude-sonnet-5", "model: m\n  api_key: sk-secret")
    with pytest.raises(ValueError, match="environment"):
        load_config(write(tmp_path, text))


def test_unknown_backend_rejected(tmp_path: Path) -> None:
    text = VALID.replace("backend: anthropic", "backend: gemini")
    with pytest.raises(ValueError, match="backend"):
        load_config(write(tmp_path, text))


def test_openai_compatible_requires_base_url(tmp_path: Path) -> None:
    text = VALID.replace("backend: anthropic", "backend: openai_compatible")
    with pytest.raises(ValueError, match="base_url"):
        load_config(write(tmp_path, text))


def test_missing_model_rejected(tmp_path: Path) -> None:
    text = VALID.replace("  model: claude-sonnet-5\n", "")
    with pytest.raises(ValueError, match="model"):
        load_config(write(tmp_path, text))


def test_password_falls_back_to_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = VALID.replace("  password: pw\n", "")
    monkeypatch.setenv("QUERYAGENT_DB_PASSWORD", "from-env")
    config = load_config(write(tmp_path, text))
    assert config.database.password == "from-env"


def test_missing_password_everywhere_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = VALID.replace("  password: pw\n", "")
    monkeypatch.delenv("QUERYAGENT_DB_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="password"):
        load_config(write(tmp_path, text))


SQLITE_DB_SECTION = """\
database:
  type: sqlite
  path: examples/demo_ecommerce/demo_shop.db
"""


def test_sqlite_config_needs_only_path(tmp_path: Path) -> None:
    text = VALID.split("database:")[0] + SQLITE_DB_SECTION
    config = load_config(write(tmp_path, text))
    assert config.database.type == "sqlite"
    assert config.database.path.endswith("demo_shop.db")


def test_sqlite_config_requires_path(tmp_path: Path) -> None:
    text = VALID.split("database:")[0] + "database:\n  type: sqlite\n"
    with pytest.raises(ValueError, match="path"):
        load_config(write(tmp_path, text))


CLICKHOUSE_DB_SECTION = """\
database:
  type: clickhouse
  host: 127.0.0.1
  database: demo_shop
"""


def test_temperature_parsed_and_defaults_to_none(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, VALID))
    assert config.llm.temperature is None
    text = VALID.replace("model: claude-sonnet-5", "model: m\n  temperature: 0")
    config = load_config(write(tmp_path, text))
    assert config.llm.temperature == 0.0


def test_negative_temperature_rejected(tmp_path: Path) -> None:
    text = VALID.replace("model: claude-sonnet-5", "model: m\n  temperature: -1")
    with pytest.raises(ValueError, match="temperature"):
        load_config(write(tmp_path, text))


def test_clickhouse_config_defaults(tmp_path: Path) -> None:
    text = VALID.split("database:")[0] + CLICKHOUSE_DB_SECTION
    config = load_config(write(tmp_path, text))
    assert config.database.type == "clickhouse"
    assert config.database.port == 9000  # native protocol default
    assert config.database.user == "default"
    assert config.database.password == ""  # CH default user has no password
