---
status: closed
type: task
blocked_by: [06]
claimed_by: fable-session
---
# T7 — 失因分析与改进

## Question
dev 集失败题的失败原因分几类？其中哪些是我能修的？

## Work
- 逐题看 trace（T2 的产物在这里第一次派上用场），把失败归类，至少分清：
  模型能力上限 / prompt 或 context 策略问题 / 金标本身有争议 /
  harness 缺陷。
- 只对「prompt 或 context 策略」类做改进（边界见 map Notes）。
- **每次改动都过自建集 gate**：首次 15/18 · 自修正后 17–18/18 ·
  追问 4/4，任一回退即回滚。
- 成功判据是**解释清楚每一类**，不是提升多少 pp；没提升也如实发布。

## Done when
- `eval/results/dev-failure-analysis.md`：每类失败有代表案例、根因、
  可修/不可修判断。
- 若有改动：dev 复跑 + 自建集 gate 均通过。

## Resolution (closed 2026-08-19)

完整分析见 [eval/results/dev-failure-analysis.md](../../../eval/results/dev-failure-analysis.md)。
20 个失败全部是「结果集不同」（无崩溃/超时/语法错），分三类：

- **A 投影不匹配 10/20（50%）—— 值算对了、形状不对**。agent 附带上下文列、
  该 DISTINCT 时没 DISTINCT。**可修**，且修法是通用原则（系统提示加
  「只 select 问题所要的，上下文写进回答文字」），不是针对题目的 hack。
- **B 金标本身有争议 5/20（25%）—— 不可修也不该修**。如「有多少病人」
  gold 却 `COUNT(T1.ID)` 数 join 后行数；「posted it last time」歧义。
  这类反过来论证了口径声明的价值。
- **C 真正的语义错误 5/20（25%）** —— 漏过滤、多跳 join 与复杂聚合的
  口径细节，prompt 改不动。与 T5 结论一致：这是强模型的优势区间。

**改进效果**：dev 自修正后 33% → 47%（+14pp），首次 23% → 30%。
自建集 gate 复跑两次未回退（自修正后 17-18/18、追问 4/4）。
