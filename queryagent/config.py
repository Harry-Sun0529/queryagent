"""Config loading: one config.yaml, dataclasses + hand-written validation.

No pydantic by design — dependency minimalism is a stated selling point
(spec §二/§四). API keys never live in config files; they are read from
environment variables only (``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``),
and the loader actively rejects credential-looking keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_FORBIDDEN_LLM_KEYS = {"api_key", "apikey", "key", "token", "secret"}
_SUPPORTED_LLM_BACKENDS = {"anthropic", "openai_compatible"}
_SUPPORTED_DB_TYPES = {"mysql"}  # v0.1.1 adds sqlite; clickhouse behind an extra
_DB_PASSWORD_ENV = "QUERYAGENT_DB_PASSWORD"


@dataclass(frozen=True)
class LLMConfig:
    """LLM backend selection; ``base_url`` only applies to openai_compatible."""

    backend: str
    model: str
    base_url: str | None = None


@dataclass(frozen=True)
class DatabaseConfig:
    """Active data source. v0.1.0 supports a single source per config."""

    type: str
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class SafetyConfig:
    """Execution limits enforced at the Connector layer."""

    timeout_s: int = 10
    max_rows: int = 200


@dataclass(frozen=True)
class AppConfig:
    """Top-level application config."""

    llm: LLMConfig
    database: DatabaseConfig
    safety: SafetyConfig
    metrics_path: str | None = None


def load_config(path: str | Path) -> AppConfig:
    """Load and validate a config.yaml file.

    Args:
        path: Path to the YAML config file.

    Returns:
        The validated application config.

    Raises:
        ValueError: On any structural or semantic problem, with an actionable
            message (which key, which section, what to do).
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return AppConfig(
        llm=_load_llm(_section(raw, "llm")),
        database=_load_database(_section(raw, "database")),
        safety=_load_safety(raw.get("safety") or {}),
        metrics_path=_opt_str(raw, "metrics_path"),
    )


def _load_llm(section: dict[str, Any]) -> LLMConfig:
    forbidden = {key for key in section if str(key).lower() in _FORBIDDEN_LLM_KEYS}
    if forbidden:
        raise ValueError(
            f"llm section contains credential-like keys {sorted(forbidden)}; API keys must "
            "come from environment variables (ANTHROPIC_API_KEY / OPENAI_API_KEY), never config"
        )
    backend = _req_str(section, "backend", "llm")
    if backend not in _SUPPORTED_LLM_BACKENDS:
        raise ValueError(
            f"llm.backend must be one of {sorted(_SUPPORTED_LLM_BACKENDS)}, got '{backend}'"
        )
    base_url = _opt_str(section, "base_url")
    if backend == "openai_compatible" and not base_url:
        raise ValueError("llm.base_url is required when llm.backend is 'openai_compatible'")
    return LLMConfig(backend=backend, model=_req_str(section, "model", "llm"), base_url=base_url)


def _load_database(section: dict[str, Any]) -> DatabaseConfig:
    db_type = _req_str(section, "type", "database")
    if db_type not in _SUPPORTED_DB_TYPES:
        raise ValueError(
            f"database.type must be one of {sorted(_SUPPORTED_DB_TYPES)} in v0.1.0, "
            f"got '{db_type}'"
        )
    password = _opt_str(section, "password") or os.environ.get(_DB_PASSWORD_ENV)
    if password is None:
        raise ValueError(
            "database.password is missing; set it in config (local demo only) "
            f"or via the {_DB_PASSWORD_ENV} environment variable"
        )
    return DatabaseConfig(
        type=db_type,
        host=_req_str(section, "host", "database"),
        port=_pos_int(section, "port", 3306, "database"),
        user=_req_str(section, "user", "database"),
        password=password,
        database=_req_str(section, "database", "database"),
    )


def _load_safety(section: dict[str, Any]) -> SafetyConfig:
    if not isinstance(section, dict):
        raise ValueError("safety section must be a mapping")
    return SafetyConfig(
        timeout_s=_pos_int(section, "timeout_s", 10, "safety"),
        max_rows=_pos_int(section, "max_rows", 200, "safety"),
    )


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"config must contain a '{name}' mapping section")
    return value


def _req_str(section: dict[str, Any], key: str, where: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}.{key} is required and must be a non-empty string")
    return value


def _opt_str(section: dict[str, Any], key: str) -> str | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string when present")
    return value


def _pos_int(section: dict[str, Any], key: str, default: int, where: str) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{where}.{key} must be a positive integer")
    return value
