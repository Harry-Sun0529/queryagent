"""Incremental persistence for eval runs.

An expanded suite is ~45 minutes of paid API calls. Writing the report only
at the end means a network blip at minute 40 discards everything — the same
class of defect as a suite aborting on one bad database, with a different
trigger. Each finished case is therefore appended to a JSONL log as it
completes, and ``--resume`` reuses that log instead of paying twice.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

from queryagent.evals.cases import EvalCase
from queryagent.evals.cost import TokenTotals
from queryagent.evals.runner import CaseResult


def result_to_dict(result: CaseResult) -> dict[str, Any]:
    """Serialise one scored case (nested dataclasses included)."""
    return dataclasses.asdict(result)


def result_from_dict(data: dict[str, Any]) -> CaseResult:
    """Rebuild a scored case, restoring tuple-typed fields JSON flattened."""
    payload = dict(data)
    case = _rebuild(EvalCase, payload.pop("case", {}))
    usage = _rebuild(TokenTotals, payload.pop("usage", {}))
    return _rebuild(CaseResult, {**payload, "case": case, "usage": usage})


def _rebuild(cls: type, payload: dict[str, Any]) -> Any:
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        if field.name not in payload:
            continue
        value = payload[field.name]
        if isinstance(value, list) and "tuple" in str(field.type):
            value = tuple(value)
        kwargs[field.name] = value
    return cls(**kwargs)


class ResumeMismatch(Exception):
    """The log on disk came from a differently configured run."""


class ResultLog:
    """Append-only log of finished cases, next to the report.

    The first line records the run's signature (model, cases source, turn
    limit). ``--resume`` refuses a log whose signature differs: mixing two
    models' results into one report produces a number nobody can explain,
    which is worse than having no number. Without ``resume`` an existing log
    is discarded rather than silently inherited.
    """

    def __init__(
        self, path: Path, *, resume: bool = False, signature: str = ""
    ) -> None:
        self.path = path
        self.signature = signature
        self._done: dict[str, CaseResult] = {}
        self._handle: TextIO | None = None
        if not path.exists():
            return
        if not resume:
            path.unlink()
            return
        previous = _read_signature(path)
        # An empty signature means the caller is inspecting the log, not
        # continuing a run; only a real run declares one and can conflict.
        if signature and previous is not None and previous != signature:
            raise ResumeMismatch(
                f"{path} 来自不同的运行配置（之前：{previous}；现在：{signature}）"
            )
        for result in _read(path):
            self._done[result.case.id] = result

    def completed(self) -> dict[str, CaseResult]:
        """Cases already scored in a previous run, by case id."""
        return dict(self._done)

    def append(self, result: CaseResult) -> None:
        """Persist one finished case immediately."""
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fresh = not self.path.exists()
            self._handle = self.path.open("a", encoding="utf-8")
            if fresh:
                json.dump(
                    {"_signature": self.signature}, self._handle, ensure_ascii=False
                )
                self._handle.write("\n")
        json.dump(result_to_dict(result), self._handle, ensure_ascii=False)
        self._handle.write("\n")
        self._handle.flush()  # the point is surviving an abrupt end

    def close(self) -> None:
        """Close the log file if it was opened."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def _read_signature(path: Path) -> str | None:
    """The signature line written when the log was created, if present."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict) and "_signature" in payload:
            return str(payload["_signature"])
        return None
    return None


def _read(path: Path) -> Iterator[CaseResult]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if isinstance(payload, dict) and "_signature" in payload:
                continue
            yield result_from_dict(payload)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            continue  # a partial tail line is expected after a kill
