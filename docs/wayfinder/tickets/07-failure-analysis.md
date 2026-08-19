---
status: open
type: task
blocked_by: [06]
claimed_by:
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
