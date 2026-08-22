---
status: open
type: task
blocked_by: []
claimed_by:
---
# T22 — 结果比对不得把不同时刻判为相等

## Question
`normalize_value` 对 datetime 用 `strftime("%Y-%m-%d %H:%M:%S")`，**丢掉了
时区**。实测 `UTC 12:00` 与 `+08:00 12:00` 被判为同一个值——它们相差 8 小时。
当前三个方言多返回 naive datetime 所以没暴露，但比对逻辑是 eval 的地基。

## Work
时区感知的 datetime 归一化到 UTC 再格式化；naive 的保持原样（不臆测时区）。

## Seams (tdd)
1. 两个不同时刻的 tz-aware datetime 不相等。
2. 同一时刻的不同表示（UTC vs +08）相等。
3. naive datetime 行为不变（回归保护）。

## Done when
- 三个 seam 测试绿；既有比对测试全部不变绿。
