"""Measure the faithfulness judge against the labelled pairs (plan 2).

    python eval/run_faithfulness_check.py --config examples/demo_ecommerce/config.sqlite.yaml \\
        --repeat 3 --output <dir>

The judge is a model, so before it may say anything on a confirmation sheet
it is graded here. Reported per run and never averaged away:

- **recall**: of the pairs labelled unfaithful, how many it called unfaithful;
- **false alarms**: of the pairs labelled faithful, how many it called
  unfaithful (a warning that cries wolf teaches people to stop reading it);
- **unsure**: how often it declined, on either side;
- the **hard** pairs on their own — a quantifier, a boundary, a clause left
  out — because a set nothing fails on measures nothing;
- the **adversarial** pairs on their own — a quote or restatement telling
  the judge what to answer;
- agreement between runs, since the model has no seed.

Pairs are judged in batches, as a sheet's rules would be. Needs the model
key the config's backend reads. Exit 0 when the run completed; whether the
numbers are good enough is a decision recorded elsewhere, not an exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from queryagent.config import load_config  # noqa: E402
from queryagent.llm import make_backend  # noqa: E402
from queryagent.workflow.faithfulness import Verdict, judge  # noqa: E402

SAMPLES = Path(__file__).parent / "knowledge" / "faithfulness.yaml"
BATCH = 6


def run_once(backend: object, items: list[dict[str, object]]) -> tuple[list[str], float]:
    """Verdicts for every item, in file order, and the seconds it took."""
    started = time.monotonic()
    verdicts: list[str] = []
    for start in range(0, len(items), BATCH):
        batch = items[start : start + BATCH]
        pairs = [(str(item["quote"]), str(item["restatement"])) for item in batch]
        verdicts.extend(j.verdict.value for j in judge(backend, pairs))  # type: ignore[arg-type]
    return verdicts, time.monotonic() - started


def score(items: list[dict[str, object]], verdicts: list[str]) -> dict[str, object]:
    unfaithful = [v for item, v in zip(items, verdicts, strict=True) if not item["faithful"]]
    faithful = [v for item, v in zip(items, verdicts, strict=True) if item["faithful"]]
    adversarial = [
        (item, v) for item, v in zip(items, verdicts, strict=True) if item["kind"] == "adversarial"
    ]
    wrong = [
        f"{item['id']}（标注{'忠实' if item['faithful'] else '不忠实'}，判为 {v}）"
        for item, v in zip(items, verdicts, strict=True)
        if v != (Verdict.FAITHFUL.value if item["faithful"] else Verdict.UNFAITHFUL.value)
    ]
    hard = [(item, v) for item, v in zip(items, verdicts, strict=True) if item["kind"] == "hard"]
    return {
        "hard_recall": (
            sum(1 for item, v in hard if not item["faithful"] and v == Verdict.UNFAITHFUL.value),
            sum(1 for item, _ in hard if not item["faithful"]),
        ),
        "hard_false_alarms": (
            sum(1 for item, v in hard if item["faithful"] and v == Verdict.UNFAITHFUL.value),
            sum(1 for item, _ in hard if item["faithful"]),
        ),
        "recall": (unfaithful.count(Verdict.UNFAITHFUL.value), len(unfaithful)),
        "false_alarms": (faithful.count(Verdict.UNFAITHFUL.value), len(faithful)),
        "unsure": verdicts.count(Verdict.UNSURE.value),
        "adversarial_held": (
            sum(
                1
                for item, v in adversarial
                if v == (Verdict.FAITHFUL.value if item["faithful"] else Verdict.UNFAITHFUL.value)
            ),
            len(adversarial),
        ),
        "wrong": wrong,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="examples/demo_ecommerce/config.sqlite.yaml")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    data = yaml.safe_load(SAMPLES.read_text(encoding="utf-8"))
    items = data["items"]
    backend = make_backend(config.llm)
    runs = []
    for index in range(args.repeat):
        verdicts, seconds = run_once(backend, items)
        result = score(items, verdicts)
        runs.append({"verdicts": verdicts, "seconds": round(seconds, 1), **result})
        hit, total = result["recall"]  # type: ignore[misc]
        alarms, clean = result["false_alarms"]  # type: ignore[misc]
        print(
            f"run {index + 1}: recall {hit}/{total}  false alarms {alarms}/{clean}  "
            f"unsure {result['unsure']}  adversarial {result['adversarial_held']}  {seconds:.0f}s"
        )
    stable = sum(
        1 for position in range(len(items)) if len({run["verdicts"][position] for run in runs}) == 1
    )
    reviewed = data.get("reviewed_by")
    lines = [
        "# 忠实性评审量测",
        "",
        f"- 模型：{config.llm.model}；样本 {len(items)} 条，每批 {BATCH} 条，重复 {args.repeat} 次",
        f"- 标签复核人：{reviewed or '**尚无（标签由 AI 起草，未经人复核，数字不可对外引用）**'}",
        f"- 各次判定完全一致的样本：{stable}/{len(items)}",
        "",
        "| 次 | 不忠实样本召回 | 忠实样本误报 | 其中边界样本召回 | 边界样本误报 "
        "| 无法判断 | 对抗样本守住 | 耗时 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for index, run in enumerate(runs, 1):
        lines.append(
            f"| {index} | {run['recall'][0]}/{run['recall'][1]} "
            f"| {run['false_alarms'][0]}/{run['false_alarms'][1]} "
            f"| {run['hard_recall'][0]}/{run['hard_recall'][1]} "
            f"| {run['hard_false_alarms'][0]}/{run['hard_false_alarms'][1]} | {run['unsure']} "
            f"| {run['adversarial_held'][0]}/{run['adversarial_held'][1]} | {run['seconds']}s |"
        )
    lines.extend(["", "## 判错的样本", ""])
    for index, run in enumerate(runs, 1):
        lines.append(f"- 第 {index} 次：" + ("；".join(run["wrong"]) or "无"))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "faithfulness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.output / "faithfulness.json").write_text(
        json.dumps({"reviewed_by": reviewed, "runs": runs}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"report -> {args.output / 'faithfulness.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
