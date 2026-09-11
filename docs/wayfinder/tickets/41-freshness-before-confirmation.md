---
status: open
type: task
blocked_by: [40]
claimed_by:
---
# T41 — 确认前的新鲜度提醒

## Question

v0.8 只能在执行后告诉你「只覆盖到 08-22」，因为确认前不查询是 I2。确认单本该提前提醒不完整
的月份。怎样在不削弱确认门的前提下做到？

## Work

- 映射可声明 `freshness: {lag_days: N}`；确认单零查询给出预期最新日期与不完整提示；执行后实测
  比声明滞后时，结果点名滞后天数。
- `workflow.freshness_before_confirm: declared | probe | off`，默认 `declared`。`probe` 时，确认
  前只允许编译器生成的 `MAX(time_column)` 探测：短超时、按表缓存、计入预算、不进哈希；执行时
  照旧重新探测。
- 口径未定时每个候选口径各一条探测，按表去重。
- ADR-010：I2 收窄为「确认前不执行任何业务查询」。

## Done when

- G8–G11；真机：声明 T+1 后「本月成交额」确认单零查询给出预期、执行后点名滞后；`probe` 模式下
  确认单出现探测结果，缓存期内再问不再探测。
