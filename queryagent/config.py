"""Config loading: one config.yaml, dataclasses + hand-written validation.

No pydantic by design — dependency minimalism is a stated selling point
(spec §二/§四). API keys never live in config files; they are read from
environment variables only (``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY``),
and the loader actively rejects credential-looking keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_FORBIDDEN_LLM_KEYS = {"api_key", "apikey", "key", "token", "secret"}
_SUPPORTED_LLM_BACKENDS = {"anthropic", "openai_compatible"}
_SUPPORTED_DB_TYPES = {"mysql", "sqlite", "clickhouse"}
_DB_PASSWORD_ENV = "QUERYAGENT_DB_PASSWORD"


@dataclass(frozen=True)
class LLMConfig:
    """LLM backend selection; ``base_url`` only applies to openai_compatible.

    ``temperature=None`` means the provider default; 0 is recommended for
    eval runs (reproducible SQL conventions and clarify decisions).
    """

    backend: str
    model: str
    base_url: str | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class DatabaseConfig:
    """Active data source; one source per config, switch by editing the file.

    Server databases (mysql) use host/port/user/password/database;
    file databases (sqlite) use ``path`` only.
    """

    type: str
    host: str = ""
    port: int = 0
    user: str = ""
    password: str = ""
    database: str = ""
    path: str = ""


@dataclass(frozen=True)
class SafetyConfig:
    """Execution limits enforced at the Connector layer."""

    timeout_s: int = 10
    max_rows: int = 200


@dataclass(frozen=True)
class WorkflowConfig:
    """The confirmation-gated query flow (v0.6, `queryagent flow`).

    ``mappings_path`` is the maintainer-declared 口径 → SQL table. Without
    one the flow can prepare and confirm but has nothing it is allowed to
    execute, which is the intended failure: guessing a query is the thing
    this layer exists to prevent.

    ``state_path`` holds drafts, confirmations and runs. It is a local
    single-process store; running two replicas against one file has not been
    designed for and must not be assumed to work.
    """

    mappings_path: str | None = None
    state_path: str = ".queryagent/workflow.db"


@dataclass(frozen=True)
class KnowledgeSource:
    """One directory of documents, and the workspace that may see it."""

    path: str
    workspace: str


@dataclass(frozen=True)
class KnowledgeConfig:
    """Document evidence (v0.6, slice 1B).

    Absent means the feature is off: ``flow`` builds drafts from
    ``metrics.yaml`` exactly as before. Presence is the switch, rather than a
    boolean flag, so there is no half-configured state to reason about.

    ``root`` confines every source path. Document import reads whatever it
    finds, and that is a file-system read path which no other layer of this
    codebase has — an unconfined one could pull `.env` or a credentials file
    into a model prompt.
    """

    root: str = ""
    index_path: str = ".queryagent/knowledge.db"
    sources: tuple[KnowledgeSource, ...] = ()

    @property
    def enabled(self) -> bool:
        return bool(self.sources)


@dataclass(frozen=True)
class AppConfig:
    """Top-level application config."""

    llm: LLMConfig
    database: DatabaseConfig
    safety: SafetyConfig
    metrics_path: str | None = None
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    trace: bool = True  # record event streams to .queryagent/traces/
    trace_dir: str | None = None  # where; default is relative to the cwd


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
        workflow=_load_workflow(raw.get("workflow") or {}),
        knowledge=_load_knowledge(raw.get("knowledge") or {}),
        trace=_opt_bool(raw, "trace", default=True),
        trace_dir=_opt_str(raw, "trace_dir"),
    )


def _load_knowledge(section: dict[str, Any]) -> KnowledgeConfig:
    if not isinstance(section, dict):
        raise ValueError("knowledge section must be a mapping")
    _reject_credential_keys(section, "knowledge")
    _reject_credential_keys(section.get("embedding") or {}, "knowledge.embedding")
    raw_sources = section.get("sources") or []
    if not isinstance(raw_sources, list):
        raise ValueError("knowledge.sources must be a list when present")
    root = _opt_str(section, "root") or ""
    sources = []
    for index, item in enumerate(raw_sources):
        where = f"knowledge.sources[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{where}: each source must be a mapping")
        path = _req_str(item, "path", where)
        workspace = _req_str(item, "workspace", where)
        if root and not _within(root, path):
            raise ValueError(
                f"{where}: '{path}' is outside knowledge.root '{root}'. "
                "Document import reads every file it finds, so the root is what "
                "keeps it away from credentials and unrelated data."
            )
        sources.append(KnowledgeSource(path=path, workspace=workspace))
    return KnowledgeConfig(
        root=root,
        index_path=_opt_str(section, "index_path") or ".queryagent/knowledge.db",
        sources=tuple(sources),
    )


def _within(root: str, path: str) -> bool:
    """True when ``path`` resolves inside ``root``.

    Resolves both sides so a symlink cannot step out of the root, which is
    the whole reason the check exists.
    """
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return False
    return True


def _reject_credential_keys(section: Any, where: str) -> None:
    """Refuse credential-looking keys in any config section.

    Was inlined in the LLM loader, so every new section silently opted out of
    it. Keys belong in environment variables (spec §二).
    """
    if not isinstance(section, dict):
        return
    forbidden = {key for key in section if str(key).lower() in _FORBIDDEN_LLM_KEYS}
    if forbidden:
        raise ValueError(
            f"{where} section contains credential-like keys {sorted(forbidden)}; "
            "API keys must come from environment variables, never config"
        )


def _load_workflow(section: dict[str, Any]) -> WorkflowConfig:
    if not isinstance(section, dict):
        raise ValueError("workflow section must be a mapping")
    return WorkflowConfig(
        mappings_path=_opt_str(section, "mappings_path"),
        state_path=_opt_str(section, "state_path") or ".queryagent/workflow.db",
    )


def _load_llm(section: dict[str, Any]) -> LLMConfig:
    _reject_credential_keys(section, "llm")
    backend = _req_str(section, "backend", "llm")
    if backend not in _SUPPORTED_LLM_BACKENDS:
        raise ValueError(
            f"llm.backend must be one of {sorted(_SUPPORTED_LLM_BACKENDS)}, got '{backend}'"
        )
    base_url = _opt_str(section, "base_url")
    if backend == "openai_compatible" and not base_url:
        raise ValueError("llm.base_url is required when llm.backend is 'openai_compatible'")
    return LLMConfig(
        backend=backend,
        model=_req_str(section, "model", "llm"),
        base_url=base_url,
        temperature=_opt_number(section, "temperature"),
    )


def _load_database(section: dict[str, Any]) -> DatabaseConfig:
    db_type = _req_str(section, "type", "database")
    if db_type not in _SUPPORTED_DB_TYPES:
        raise ValueError(
            f"database.type must be one of {sorted(_SUPPORTED_DB_TYPES)}, got '{db_type}'"
        )
    if db_type == "sqlite":
        return DatabaseConfig(type=db_type, path=_req_str(section, "path", "database"))
    if db_type == "clickhouse":
        # ClickHouse's default user ships with an empty password, so unlike
        # mysql a missing password is not an error here.
        return DatabaseConfig(
            type=db_type,
            host=_req_str(section, "host", "database"),
            port=_pos_int(section, "port", 9000, "database"),
            user=_opt_str(section, "user") or "default",
            password=_opt_str(section, "password") or os.environ.get(_DB_PASSWORD_ENV) or "",
            database=_req_str(section, "database", "database"),
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


def _opt_bool(section: dict[str, Any], key: str, *, default: bool) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be true or false when present")
    return value


def _opt_number(section: dict[str, Any], key: str) -> float | None:
    value = section.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{key} must be a non-negative number when present")
    return float(value)


def _pos_int(section: dict[str, Any], key: str, default: int, where: str) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{where}.{key} must be a positive integer")
    return value
