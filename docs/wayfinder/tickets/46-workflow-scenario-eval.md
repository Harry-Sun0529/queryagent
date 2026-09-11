---
status: open
type: task
blocked_by: [44]
claimed_by:
---
# T46 — 场景评测：量本产品真正保证的东西

## Question

现有评测只量 Text-to-SQL 准确率。该问的有没有问、数字对不对得上、有没有未经确认就执行、有没有
越权——这些才是本产品的价值，却没有一个数。

## Work

- `eval/workflow/scenarios.yaml`：约 20 个场景，逐一对应 T01–T14、F4–F14、G3/G12–G17、H1/H3。
- `eval/run_workflow_scenarios.py`：脚本化用户回答，计数执行器，金丝雀串检测泄露与注入；复用
  `evals/identity.py` 签名。
- 数字对照一律来自独立参照（Python 逐行重算或另一套原生函数）。
- 确定性子集由 `tests/test_scenarios.py` 读同一份 YAML 进 CI；涉及文档抽取的用 DeepSeek 跑 3 次
  报区间。

## Done when

- H10–H11；报告落在 `eval/results/workflow-scenarios-<日期>/`，未确认执行、跨空间泄露、注入生效
  三项为 0。
