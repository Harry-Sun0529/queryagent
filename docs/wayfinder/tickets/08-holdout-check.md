---
status: closed
type: task
blocked_by: [07]
claimed_by: fable-session
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

## Resolution (closed 2026-08-19)

封存的 seed 42 三十题在 v0.3.0 验收时跑了**一次**：首次 10/30 (33%)、
自修正后 **16/30 (53%)**，报告存 `eval/results/bird-test-holdout-v0.3.0.md`。

**泛化度量**：dev 上的提升 +14pp（33%→47%），test 相对 v0.1.0 锚点
（47%）为 +6pp —— **不到一半兑现**，这正是过拟合的典型形态，也是切分
方案存在的意义。

**诚实标注**：两个 test 数字的配置并不完全可比（v0.1.0 用 deepseek-chat
别名即非思考模式 + 旧代码；v0.3.0 是 v4-flash 思考模式 + 全部改动）。
干净的前后对照只存在于 dev 上；test 按纪律只跑一次，因此它是一个验收
数字而非受控实验。这个局限必须写进 README。
