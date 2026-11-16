"""``eval``: scored suites over the agent path, with checkpointing and an outage guard.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import sys
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from queryagent.cli.chat import SessionRunQuestion, _make_run_question
from queryagent.cli.errors import (
    EXIT_EVAL_FAILED,
    EXIT_OK,
    EXIT_TEMPORARY_FAILURE,
    EXIT_USER_ERROR,
)
from queryagent.config import AppConfig, load_config
from queryagent.connectors import make_connector
from queryagent.connectors.base import Connector
from queryagent.connectors.sqlite import SQLiteConnector
from queryagent.evals.cases import EvalCase, load_cases
from queryagent.evals.checkpoint import ResultLog, ResumeMismatch
from queryagent.evals.identity import run_signature
from queryagent.evals.public import load_subset
from queryagent.evals.runner import (
    CaseResult,
    render_report,
    run_case,
    unscoreable_case,
)

# Consecutive cases lost to an unreachable provider before a run gives up.
# Burning a 200-case suite against a dead endpoint produces a report that
# reads like a measurement of 0%; stopping early keeps it honest and, thanks
# to checkpointing, costs nothing to resume.
MAX_CONSECUTIVE_OUTAGES = 5

class UpstreamOutage(Exception):
    """Too many consecutive cases went unmeasured.

    Carries the last case's reason so the exit code can match the cause: a
    provider outage is worth retrying, an exhausted balance or a rejected key
    is not, and telling a retry loop otherwise makes it spin forever.
    """

    def __init__(self, message: str, *, reason: str, retryable: bool) -> None:
        super().__init__(message)
        self.reason = reason
        self.retryable = retryable


class _OutageGuard:
    """Counts consecutive unmeasured cases across the whole suite."""

    def __init__(self, limit: int = MAX_CONSECUTIVE_OUTAGES) -> None:
        self._limit = limit
        self._streak = 0

    def record(self, result: CaseResult) -> None:
        """Track one scored case; raise once the streak passes the limit."""
        self._streak = self._streak + 1 if result.unmeasured else 0
        if self._streak >= self._limit:
            raise UpstreamOutage(
                f"{self._streak} 个用例连续未能测量，已中止本次运行"
                f"（最后一次：{result.failure_reason[:160]}）",
                reason=result.failure_reason,
                retryable=result.retryable,
            )

def _cmd_eval(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if args.backend or args.model or args.base_url:
        # replace() keeps unrelated fields (notably temperature) intact —
        # rebuilding LLMConfig from scratch silently dropped them once.
        config = dataclasses.replace(
            config,
            llm=dataclasses.replace(
                config.llm,
                backend=args.backend or config.llm.backend,
                model=args.model or config.llm.model,
                base_url=args.base_url or config.llm.base_url,
            ),
        )
    if args.public and not args.db_dir:
        print("--public requires --db-dir", file=sys.stderr)
        return 2
    if (
        args.resume
        and not args.public
        and config.database.type != "sqlite"
        and not args.data_version
    ):
        print("--resume on a server database requires --data-version", file=sys.stderr)
        return 2
    signature = run_signature(
        config,
        Path(args.public or args.cases),
        max_turns=args.max_turns,
        db_dir=Path(args.db_dir) if args.public else None,
        data_version=args.data_version,
    )
    try:
        log = ResultLog(
            Path(args.output).with_suffix(".partial.jsonl"),
            resume=args.resume,
            signature=signature,
        )
    except ResumeMismatch as exc:
        print(f"[错误] 无法续跑：{exc}", file=sys.stderr)
        print("  → 删除该 .partial.jsonl 重新开始，或改回原配置。", file=sys.stderr)
        return 2
    try:
        return _run_eval(args, config, log)
    except UpstreamOutage as exc:
        log.close()
        print(f"[错误] {exc}", file=sys.stderr)
        if exc.retryable:
            print(
                "  → 这是上游故障，不是测量结果。稍后用 --resume 续跑；"
                "已完成的用例不会重付。",
                file=sys.stderr,
            )
            return EXIT_TEMPORARY_FAILURE
        print(
            "  → 服务方拒绝了请求（余额、配额或 key 的问题），重试不会好转。"
            "处理后用 --resume 续跑；已完成的用例不会重付。",
            file=sys.stderr,
        )
        return EXIT_USER_ERROR


def _run_eval(args: argparse.Namespace, config: AppConfig, log: ResultLog) -> int:
    if args.public:
        if not args.db_dir:
            print("--public requires --db-dir", file=sys.stderr)
            return 2
        # Public benchmarks have no metrics.yaml of their own; the demo's
        # e-commerce metrics must not leak into their prompts.
        public_config = dataclasses.replace(config, metrics_path=None)
        try:
            results = _eval_public(
                args.public,
                Path(args.db_dir),
                public_config,
                args.max_turns,
                log,
                args.concurrency,
            )
        finally:
            log.close()
        title = "QueryAgent Eval Report — public subset"
    else:
        try:
            results = _eval_self_built(
                args.cases, config, args.max_turns, log, args.concurrency
            )
        finally:
            log.close()
        title = "QueryAgent Eval Report — self-built cases"
    report = render_report(results, title=title, model_label=config.llm.model)
    output = Path(args.output)
    # Never lose a finished (paid-for) run to a missing folder.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    passed = sum(1 for r in results if r.passed)
    print(f"{passed}/{len(results)} cases passed; report -> {args.output}")
    passed_all = all(r.passed and r.completed is True for r in results)
    return EXIT_OK if passed_all else EXIT_EVAL_FAILED


class _WorkerPool:
    """One connector and one wired runner per thread.

    SQLite connections cannot be shared between threads, and a per-thread
    backend keeps one slow call from blocking another. Everything created
    here is closed by the caller's ExitStack.
    """

    def __init__(
        self,
        build: Callable[[contextlib.ExitStack], tuple[Connector, SessionRunQuestion]],
        stack: contextlib.ExitStack,
    ) -> None:
        self._build = build
        self._stack = stack
        self._local = threading.local()
        self._lock = threading.Lock()

    def get(self) -> tuple[Connector, SessionRunQuestion]:
        """The calling thread's worker, built on first use."""
        worker = getattr(self._local, "worker", None)
        if worker is None:
            with self._lock:  # ExitStack registration is not thread-safe
                worker = self._build(self._stack)
            self._local.worker = worker
        return worker


def _run_batch(
    cases: Sequence[EvalCase],
    *,
    pool: _WorkerPool,
    done: dict[str, CaseResult],
    results: list[CaseResult],
    log: ResultLog,
    guard: _OutageGuard,
    concurrency: int,
) -> None:
    """Score ``cases``, in order, optionally several at a time.

    Completed cases are persisted by one writer immediately. The caller sorts
    the report later. Outage streaks follow completion order; at most
    ``concurrency`` cases are in flight, and these are drained on an outage.
    """
    pending = [case for case in cases if case.id not in done]
    for case in cases:
        if case.id in done:
            results.append(done[case.id])

    def score(case: EvalCase) -> CaseResult:
        connector, run_question = pool.get()
        return run_case(case, run_question=run_question, connector=connector)

    if concurrency <= 1:
        for case in pending:
            _record(score(case), results, log, guard)
        return
    remaining = iter(pending)
    outage: UpstreamOutage | None = None
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        active = {
            executor.submit(score, case)
            for case in [next(remaining, None) for _ in range(concurrency)]
            if case is not None
        }
        try:
            while active:
                finished, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in finished:
                    result = future.result()
                    if outage is not None:
                        # Preserve paid-for in-flight results without restarting the run.
                        results.append(result)
                        if not result.unmeasured:
                            log.append(result)
                    else:
                        try:
                            _record(result, results, log, guard)
                        except UpstreamOutage as exc:
                            outage = exc
                    active.remove(future)
                if outage is None:
                    for _ in range(concurrency - len(active)):
                        next_case = next(remaining, None)
                        if next_case is None:
                            break
                        active.add(executor.submit(score, next_case))
        except KeyboardInterrupt:
            # Stop admission, drain the bounded in-flight set, and preserve even
            # results that completed just before Ctrl-C interrupted the writer.
            log.close()
            recovered = ResultLog(log.path, resume=True, signature=log.signature)
            saved = recovered.completed()
            try:
                for future in active:
                    result = future.result()
                    if not result.unmeasured and result.case.id not in saved:
                        recovered.append(result)
            finally:
                recovered.close()
            raise

    if outage is not None:
        raise outage


def _record(
    result: CaseResult,
    results: list[CaseResult],
    log: ResultLog,
    guard: _OutageGuard,
) -> None:
    """Collect one result, persisting it only if it was actually measured.

    An unmeasured case must be retried on the next run, so writing it to the
    resume log would bake the outage into the final number.
    """
    results.append(result)
    if not result.unmeasured:
        log.append(result)
    guard.record(result)


def _eval_self_built(
    cases_path: str,
    config: AppConfig,
    max_turns: int,
    log: ResultLog,
    concurrency: int = 1,
) -> list[CaseResult]:
    cases = load_cases(cases_path)
    done = log.completed()
    guard = _OutageGuard()
    results: list[CaseResult] = []
    with contextlib.ExitStack() as stack:
        pool = _WorkerPool(
            lambda st: _build_worker(config, max_turns, st), stack
        )
        _run_batch(
            cases,
            pool=pool,
            done=done,
            results=results,
            log=log,
            guard=guard,
            concurrency=concurrency,
        )
    results.sort(key=lambda r: [c.id for c in cases].index(r.case.id))
    return results


def _build_worker(
    config: AppConfig, max_turns: int, stack: contextlib.ExitStack
) -> tuple[Connector, SessionRunQuestion]:
    """A connector plus its wired runner, both released by ``stack``."""
    connector = make_connector(config.database)
    stack.callback(connector.close)
    return connector, _make_run_question(connector, config, max_turns, stack)


def _eval_public(
    subset_path: str,
    db_dir: Path,
    config: AppConfig,
    max_turns: int,
    log: ResultLog,
    concurrency: int = 1,
) -> list[CaseResult]:
    """Public-benchmark mode: one SQLite database (and runtime) per db_id."""
    cases = load_subset(subset_path)
    done = log.completed()
    guard = _OutageGuard()
    results: list[CaseResult] = []
    by_db: dict[str, list[EvalCase]] = {}
    for case in cases:
        by_db.setdefault(case.db_id, []).append(case)
    for db_id, db_cases in by_db.items():
        try:
            db_path = str(db_dir / db_id / f"{db_id}.sqlite")
            # Opened once up front so an unusable database fails fast, before
            # any worker or paid call; workers open their own below.
            connector = SQLiteConnector(path=db_path)
        except Exception as exc:  # noqa: BLE001
            # One unusable database costs its own cases, not the whole run —
            # a public suite is 30 paid minutes and must survive to a report.
            reason = f"database '{db_id}' unusable: {exc}"
            print(f"[warn] {reason}", file=sys.stderr)
            for case in db_cases:
                if case.id in done:
                    results.append(done[case.id])
                    continue
                _record(unscoreable_case(case, reason), results, log, guard)
            continue
        try:
            with contextlib.ExitStack() as stack:
                stack.callback(connector.close)
                def build(
                    st: contextlib.ExitStack, path: str = db_path
                ) -> tuple[Connector, SessionRunQuestion]:
                    """A fresh connector per worker.

                    Sharing one would let concurrent queries strip each
                    other's timeout: SQLite's deadline guard is installed on
                    the connection, not the statement.
                    """
                    worker_connector = SQLiteConnector(path=path)
                    st.callback(worker_connector.close)
                    return worker_connector, _make_run_question(
                        worker_connector, config, max_turns, st
                    )

                pool = _WorkerPool(build, stack)
                _run_batch(
                    db_cases,
                    pool=pool,
                    done=done,
                    results=results,
                    log=log,
                    guard=guard,
                    concurrency=concurrency,
                )
        except UpstreamOutage:
            raise
        except Exception as exc:  # noqa: BLE001
            reason = f"database '{db_id}' aborted: {type(exc).__name__}: {exc}"
            print(f"[warn] {reason}", file=sys.stderr)
            recorded = {r.case.id for r in results}
            for case in db_cases:
                if case.id in recorded:
                    continue
                result = unscoreable_case(case, reason)
                log.append(result)
                results.append(result)
    results.sort(key=lambda r: r.case.id)
    return results
