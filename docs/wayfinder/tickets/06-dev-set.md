---
status: open
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
