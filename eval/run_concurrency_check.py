"""Run the fixed dev100 serial/parallel comparison; stop on incomplete measurement.

Uses OPENAI_API_KEY from the environment. Never reads keys from the repository.
Run from any directory with the project's Python; --output must be a new directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from queryagent.evals.checkpoint import ResultLog  # noqa: E402
from queryagent.evals.cost import TokenTotals, estimate_cost_usd  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "queryagent").rglob("*.py"))
    }
    (out / "source-manifest.json").write_text(json.dumps(source, indent=2))
    records = []
    for name, concurrency in [
        ("serial-1", 1),
        ("parallel-1", 4),
        ("parallel-2", 4),
        ("serial-2", 1),
    ]:
        command = [
            sys.executable,
            "-m",
            "queryagent.cli",
            "eval",
            "--config",
            str(ROOT / "examples/demo_ecommerce/config.sqlite.yaml"),
            "--model",
            "deepseek-v4-flash",
            "--public",
            str(ROOT / "eval/public/dev-subset.json"),
            "--db-dir",
            str(ROOT / "eval/public/databases"),
            "--output",
            str(out / f"{name}.md"),
            "--concurrency",
            str(concurrency),
        ]
        print("START", name, flush=True)
        started = time.monotonic()
        with (out / f"{name}.log").open("w") as stream:
            code = subprocess.call(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        checkpoint = out / f"{name}.partial.jsonl"
        results = list(ResultLog(checkpoint, resume=True).completed().values())
        usage = sum((r.usage for r in results), TokenTotals())
        record = {
            "run": name,
            "concurrency": concurrency,
            "exit_code": code,
            "wall_seconds": round(time.monotonic() - started, 2),
            "recorded": len(results),
            "sql_hits": sum(r.passed for r in results),
            "completed_hits": sum(r.passed and r.completed is True for r in results),
            "tokens": usage.input_tokens + usage.output_tokens,
            "estimated_usd_upper_bound": estimate_cost_usd(usage, "deepseek-v4-flash"),
        }
        records.append(record)
        (out / "manifest.json").write_text(json.dumps(records, indent=2))
        print("DONE", json.dumps(record), flush=True)
        if code not in (0, 3) or len(results) != 100:
            print("STOP: incomplete measurement; see run log before restarting.", flush=True)
            return code if code not in (0, 3) else 1
    print(
        "COMPLETE: four measured runs; statistical interpretation still requires review.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
