---
status: open
type: task
blocked_by: [32]
claimed_by:
---
# T33 — 统计区间进入草案与确认

## Question

区间要以「本次约定」出现在确认单上、写进哈希、第二天执行不漂移；指标要求区间而问题
没给时，要列为缺失并让用户补。

## Work

- `PERIOD_RULE_KEY` 进 models；`required_rules` 可声明 `period`，但抽取允许键不含它（P4）。
- `MetricDraftBuilder` 注入"今天"（按 `workflow.timezone`），从问题解析区间。
- CLI `--period`，交互补写走同一个解析器，认不出就拒绝。
- 确认单把区间显示为「2026-08-01 至 2026-08-31」并注明换算自哪几个字。

## Done when

- P1、P2、P3、P4 有测试；P3 用注入时钟证明"今天确认、明天执行"跑的是确认时的日期。
