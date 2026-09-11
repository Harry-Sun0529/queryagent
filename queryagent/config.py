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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
class BudgetConfig:
    """Totals across statements, set by a maintainer (slice 1E, ADR-011).

    ``SafetyConfig`` bounds one statement; this bounds how many run, for how
    long and how many at once. ``None`` leaves an item unlimited. The whole
    section is optional and its absence means no totals at all — how every
    release before 0.9 behaved, and the rollback path.

    Nothing but this file sets these: no command-line flag, workflow rule,
    document or tool argument reaches them.
    """

    max_queries_per_request: int | None = None
    """Statements one confirmed run (its probe included) or one agent question may execute."""
    max_queries_per_day: int | None = None
    """Statements one subject may execute per business day (``workflow.timezone``)."""
    max_query_seconds_per_day: int | None = None
    """Client-measured seconds one subject's statements may take per business day."""
    max_concurrent: int | None = None
    """Requests executing at once against one state file, across processes."""
    max_rows_scanned: int | None = None
    """Rows one statement may read. ClickHouse enforces this in the engine; no
    other supported database can, so it is refused anywhere else."""


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
    timezone: str = "Asia/Shanghai"
    """Which day "今天" is when a question says 「上个月」. It does not convert
    stored timestamps: data is compared in the time it was stored in."""
    freshness_before_confirm: str = "declared"
    """What the sheet may learn about the data's reach before confirmation
    (ADR-010): ``declared`` cadence only, zero queries; ``probe`` also runs
    the compiler's ``MAX()`` probe; ``off`` says nothing until the result."""
    freshness_probe_timeout_s: int = 2
    freshness_cache_minutes: int = 10


@dataclass(frozen=True)
class KnowledgeSource:
    """One directory of documents, and the workspace that may see it."""

    path: str
    workspace: str


@dataclass(frozen=True)
class EmbeddingConfig:
    """Optional semantic retrieval over an OpenAI-compatible embeddings endpoint.

    The key is never here; it comes from ``QUERYAGENT_EMBEDDING_API_KEY``.
    Enabling this sends document text to ``base_url`` — a data-boundary
    decision for whoever deploys it, which is why it is off unless present.

    ``min_similarity`` is None to take the provider's default, which is
    calibrated for one model; set it when changing model.
    """

    base_url: str
    model: str
    min_similarity: float | None = None


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
    embedding: EmbeddingConfig | None = None

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
    budget: BudgetConfig | None = None  # None: no totals configured
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
    database = _load_database(_section(raw, "database"))
    return AppConfig(
        llm=_load_llm(_section(raw, "llm")),
        database=database,
        safety=_load_safety(raw.get("safety") or {}),
        metrics_path=_opt_str(raw, "metrics_path"),
        workflow=_load_workflow(raw.get("workflow") or {}),
        knowledge=_load_knowledge(raw.get("knowledge") or {}),
        budget=_load_budget(raw.get("budget"), database.type),
        trace=_opt_bool(raw, "trace", default=True),
        trace_dir=_opt_str(raw, "trace_dir"),
    )


_BUDGET_KEYS = (
    "max_queries_per_request",
    "max_queries_per_day",
    "max_query_seconds_per_day",
    "max_concurrent",
    "max_rows_scanned",
)


def _load_budget(section: Any, db_type: str) -> BudgetConfig | None:
    """Absent means unlimited; present means every key is a real, enforceable limit.

    An unknown key is refused because a misspelt limit limits nothing and
    says nothing. A scan limit on a database that cannot enforce it is
    refused for the same reason: a limit written down but not applied is a
    false statement about the deployment (E03).
    """
    if not section:
        return None
    if not isinstance(section, dict):
        raise ValueError("budget section must be a mapping of limits")
    unknown = sorted(str(key) for key in section if key not in _BUDGET_KEYS)
    if unknown:
        raise ValueError(
            f"budget: unknown keys {unknown}; allowed: {', '.join(_BUDGET_KEYS)}. "
            "A misspelt limit would silently limit nothing."
        )
    limits = {str(key): _pos_int(section, str(key), 1, "budget") for key in section}
    if "max_rows_scanned" in limits and db_type != "clickhouse":
        raise ValueError(
            f"budget.max_rows_scanned cannot be enforced on {db_type}: only ClickHouse limits "
            "the rows a statement reads, in the engine. Remove it rather than keep a limit "
            "that limits nothing; safety.timeout_s is what bounds a statement there."
        )
    return BudgetConfig(**limits)


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
        embedding=_load_embedding(section.get("embedding")),
    )


def _load_embedding(section: Any) -> EmbeddingConfig | None:
    if not section:
        return None
    where = "knowledge.embedding"
    if not isinstance(section, dict):
        raise ValueError(f"{where} must be a mapping")
    floor = _opt_number(section, "min_similarity")
    if floor is not None and not 0.0 < floor < 1.0:
        raise ValueError(
            f"{where}.min_similarity must be strictly between 0 and 1, got {floor}"
        )
    return EmbeddingConfig(
        base_url=_req_str(section, "base_url", where),
        model=_req_str(section, "model", where),
        min_similarity=floor,
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
    timezone = _opt_str(section, "timezone") or "Asia/Shanghai"
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"workflow.timezone: unknown time zone {timezone!r}") from exc
    mode = _opt_str(section, "freshness_before_confirm") or "declared"
    if mode not in _FRESHNESS_MODES:
        raise ValueError(
            f"workflow.freshness_before_confirm must be one of {', '.join(_FRESHNESS_MODES)}, "
            f"got {mode!r}"
        )
    return WorkflowConfig(
        mappings_path=_opt_str(section, "mappings_path"),
        state_path=_opt_str(section, "state_path") or ".queryagent/workflow.db",
        timezone=timezone,
        freshness_before_confirm=mode,
        freshness_probe_timeout_s=_pos_int(section, "freshness_probe_timeout_s", 2, "workflow"),
        freshness_cache_minutes=_pos_int(section, "freshness_cache_minutes", 10, "workflow"),
    )


# Spelled out rather than imported: config loads before the workflow package.
_FRESHNESS_MODES = ("declared", "probe", "off")


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
