---
status: open
type: task
blocked_by: [07]
claimed_by:
---
# T8 — test 集重跑与过拟合度量

## Question
在 dev 上的改进是否泛化到了从未看过的题？

## Work
- 封存的 seed 42 三十题**跑一次**（这是 ADR-004 允许的版本验收动作）。
- 报告 dev 与 test 的提升差：**这个差就是过拟合的量化度量**，也是整个
  切分方案的兑现。
- 无论结果如何都如实写进 README（包括「dev 提升但 test 没动」这种
  最尴尬的情况——它恰恰证明切分有效）。

## Done when
- test 报告落 `eval/results/`；README 的 Evaluation 章节含 dev/test 双列
  与过拟合差值的解读。
