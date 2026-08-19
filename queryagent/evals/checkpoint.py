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


class ResultLog:
    """Append-only log of finished cases, next to the report.

    ``resume`` decides whether an existing log is reused or replaced: a fresh
    run must not silently inherit results from an older, differently
    configured one.
    """

    def __init__(self, path: Path, *, resume: bool = False) -> None:
        self.path = path
        self._done: dict[str, CaseResult] = {}
        if resume and path.exists():
            for result in _read(path):
                self._done[result.case.id] = result
        elif path.exists():
            path.unlink()
        self._handle: TextIO | None = None

    def completed(self) -> dict[str, CaseResult]:
        """Cases already scored in a previous run, by case id."""
        return dict(self._done)

    def append(self, result: CaseResult) -> None:
        """Persist one finished case immediately."""
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8")
        json.dump(result_to_dict(result), self._handle, ensure_ascii=False)
        self._handle.write("\n")
        self._handle.flush()  # the point is surviving an abrupt end

    def close(self) -> None:
        """Close the log file if it was opened."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def _read(path: Path) -> Iterator[CaseResult]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            yield result_from_dict(json.loads(line))
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            continue  # a partial tail line is expected after a kill
