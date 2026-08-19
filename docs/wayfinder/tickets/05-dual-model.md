---
status: open
type: task
blocked_by: [03]
claimed_by:
---
# T5 — 强弱双模型对比（v4-flash vs v4-pro）

## Question
§七.7「同一架构下强弱模型差异」目前无法回答（原计划靠 Anthropic key，
已确认拿不到）。DeepSeek 自带强弱两档，且都支持 tool calling（已实测）。

## Work
- 自建集对 v4-flash 与 v4-pro 各跑一遍（各 3 次取区间，遵循无 seed 的
  噪声纪律）。
- 产出差异分析：差距出现在哪类 case（多步？自修正？追问判断？），
  **能力 × 成本 × 延迟三维**，回答「多花 3 倍的钱买到了什么」。
- 报告落 `eval/results/`，README 放结论摘要。

## Done when
- 两个模型的报告都在 `eval/results/`；差异分析能指名道姓说出哪类 case
  拉开差距，而不是只报总分。
