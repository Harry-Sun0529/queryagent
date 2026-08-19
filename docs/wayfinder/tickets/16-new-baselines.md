---
status: open
type: task
blocked_by: [11, 14]
claimed_by:
---
# T16 — 扩集后的新基线

## Work
- dev 100 题基线（v4-flash）
- test 200 题验收运行（**只跑一次**，跑完即封存）
- 记录 token / 成本 / 耗时 / 缓存命中率
- 用 T11 的增量落盘跑，避免 45 分钟中途失败丢结果

## Done when
- 两份报告落 `eval/results/`；新数字取代旧 30 题样本的数字成为当前值。
