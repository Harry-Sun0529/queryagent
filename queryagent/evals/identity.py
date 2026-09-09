"""Content identity for resumable experiments; no credentials enter the log."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from queryagent.config import AppConfig
from queryagent.evals.public import load_subset


def _file_digest(path: Path) -> str:
    if not path.exists():
        return "missing"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_signature(
    config: AppConfig,
    source: Path,
    *,
    max_turns: int,
    db_dir: Path | None = None,
    data_version: str | None = None,
) -> str:
    """Hash effective inputs, local snapshots and implementation, excluding secrets.

    Server data cannot be fingerprinted without querying it. Its snapshot token
    is supplied by the operator; CLI requires it for server-side resume.
    """
    database = asdict(config.database)
    database.pop("password")
    if db_dir is not None:
        paths = [
            db_dir / name / f"{name}.sqlite"
            for name in sorted({c.db_id for c in load_subset(source)})
        ]
        database = {"type": "public-sqlite", "directory": str(db_dir.resolve())}
    else:
        paths = [Path(config.database.path)] if config.database.type == "sqlite" else []
    snapshots = {
        str(path.resolve()): (_file_digest(path), _file_digest(Path(str(path) + "-wal")))
        for path in paths
    }
    package = Path(__file__).resolve().parents[1]
    code = {str(p.relative_to(package)): _file_digest(p) for p in sorted(package.rglob("*.py"))}
    payload = {
        "llm": asdict(config.llm),
        "safety": asdict(config.safety),
        "cases": _file_digest(source),
        "database": database,
        "snapshots": snapshots,
        "metrics": _file_digest(Path(config.metrics_path))
        if config.metrics_path and db_dir is None
        else None,
        "turns": max_turns,
        "date": date.today().isoformat(),
        "data_version": data_version,
        "code": code,
    }
    return (
        f"v2:{config.llm.backend}/{config.llm.model}:"
        + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    )
