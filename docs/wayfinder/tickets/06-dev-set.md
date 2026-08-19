---
status: closed
type: task
blocked_by: [03]
claimed_by: fable-session
---
# T6 — dev 集抽样与基线

## Question
要做失因分析就需要一个允许看的公开集，但 seed 42 的 30 题必须保持封存。

## Work
- `queryagent/evals/public.py` 的 `sample_cases` 加 `exclude` 参数
  （排除 test 集的 question id），新 seed = 7，抽 30 题。
- `eval/public/dev-subset.json` 进 repo（与 test 集同等可复现）。
- 11 个 BIRD 库已在本地（1.4G），零下载成本；把 dev 集需要的库补进
  `eval/public/databases/`。
- 跑 dev 集基线（v4-flash），报告存 `eval/results/`。

## Seams (tdd)
`sample_cases` 的 exclude 行为：dev 与 test 零交集、同 seed 可复现。

## Done when
- 交集为空的测试绿；dev 基线报告落盘。

## Resolution (closed 2026-08-19)

- `sample_cases` 增加 `exclude=`，dev 与 test 的不相交成为**被测试保证的
  性质**而非承诺（3 个新测试）。`--seed` / `--exclude` 也暴露到 CLI，
  任何人可从 repo 复现两个样本。
- `eval/public/dev-subset.json`（seed 7，30 题）进 repo，与 seed 42 的
  test 集零交集；11 个 BIRD 库本地已有，零下载成本。
- dev 基线（v4-flash）：首次 7/30 (23%)、自修正后 10/30 (33%)，
  每题 12,441 token / 13.4s —— BIRD 的 schema 比 demo 大得多，探索成本
  是自建集的 4 倍（3,100 token / 4.2s）。报告存
  `eval/results/dev-baseline-flash.md`。

> 注（2026-08-20）：该报告文件已在 v0.4.0 扩集时随退役样本一并移除；当前 dev 基线见 `eval/results/dev-baseline-100.md`。
