"""Run the workflow scenarios and write a report (v1.0 T46).

    python eval/run_workflow_scenarios.py --mode deterministic \
        --out eval/results/workflow-scenarios-2026-09-11
    python eval/run_workflow_scenarios.py --mode model --repeat 3 \
        --config examples/demo_ecommerce/config.sqlite.yaml \
        --out eval/results/workflow-scenarios-2026-09-11

Deterministic mode needs no key: document extraction is scripted. Model mode
reruns the scenarios that read documents against the configured model
(OPENAI_API_KEY or ANTHROPIC_API_KEY, as the config's backend requires).

Writes ``<mode>.md`` and ``<mode>.jsonl`` under ``--out``. Exits 0 when the
three gates read zero and, in deterministic mode, every scenario passed;
3 otherwise.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from queryagent.config import load_config
from queryagent.evals.identity import run_signature
from queryagent.evals.scenarios import (
    SCENARIOS,
    Recount,
    bench_today,
    demo_db,
    load_scenarios,
    outcome_record,
    render_report,
    run_suite,
    summarize,
)
from queryagent.llm import make_backend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", choices=["deterministic", "model"], default="deterministic")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--config", default="examples/demo_ecommerce/config.sqlite.yaml")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    config = dataclasses.replace(
        config, database=dataclasses.replace(config.database, path=str(demo_db()))
    )
    scenarios = load_scenarios(SCENARIOS)
    llm = dataclasses.asdict(config.llm)
    llm = {key: value for key, value in llm.items() if value is not None}
    runs = []
    for _ in range(args.repeat if args.mode == "model" else 1):
        with tempfile.TemporaryDirectory(prefix="queryagent-scenarios-") as root:
            if args.mode == "model":
                runs.append(
                    run_suite(
                        scenarios,
                        root=Path(root),
                        mode="model",
                        model=lambda: make_backend(config.llm),
                        llm=llm,
                    )
                )
            else:
                runs.append(run_suite(scenarios, root=Path(root)))

    data_end = Recount(demo_db()).data_end
    # --dirty: a report written before its own commit says so, and the run
    # signature (a digest of every source file) is the exact identity.
    commit = subprocess.run(
        ["git", "describe", "--always", "--dirty"], capture_output=True, text=True, check=False
    ).stdout.strip()
    header = {
        "日期": date.today().isoformat(),
        "代码": commit or "unknown",
        "运行签名": run_signature(config, SCENARIOS, max_turns=0),
        "演示数据最新记录": data_end.isoformat(),
        "基准「今天」": bench_today(data_end).isoformat(),
        "模型": config.llm.model if args.mode == "model" else "（抽取由脚本扮演，不调用模型）",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{args.mode}.md").write_text(
        render_report(runs, mode=args.mode, header=header), encoding="utf-8"
    )
    with (args.out / f"{args.mode}.jsonl").open("w", encoding="utf-8") as stream:
        for index, run in enumerate(runs, start=1):
            for outcome in run:
                record = {"run": index, **outcome_record(outcome)}
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    summaries = [summarize(run) for run in runs]
    for summary in summaries:
        print(
            f"passed {summary.passed}/{summary.scenarios}  unconfirmed={summary.unconfirmed} "
            f"leaks={summary.leaks} injections={summary.injections}  "
            f"values {summary.values_matched}/{summary.values}"
        )
    held = all(s.gates_hold for s in summaries)
    complete = args.mode == "model" or all(s.passed == s.scenarios for s in summaries)
    return 0 if held and complete else 3


if __name__ == "__main__":
    sys.exit(main())
