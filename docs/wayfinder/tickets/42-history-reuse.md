---
status: open
type: task
blocked_by: []
claimed_by:
---
# T42 — 沿用上次确认过的选择

## Question

alice 昨天选了首单口径，今天再问同一个指标还要重选一遍。交接文档要求可复用历史选择，但它
不是团队标准。怎样沿用而不让历史悄悄盖过文档、也不让脚本静默沿用？

## Work

- 新来源 `RuleSource.HISTORY`（「历史选择」），写明来自哪天的哪次执行，进哈希。
- `HistoryDraftBuilder` 包在 `CompositeDraftBuilder` 外，只填仍缺的键：口径、文档分歧里采用的
  写法、用户补过的缺口；不沿用区间与分组；不覆盖文档依据，不一致时点名。
- 由存储派生（drafts ⋈ confirmations ⋈ runs，成功执行过的），不另建历史表；run 记录映射指纹。
- 失效：映射指纹变化、所引文档复查不 OK、选项已不存在、超过 `history_max_age_days`；因文档
  失效不沿用时不说是哪份。
- `--yes` 不预填；`--no-history` 显式关闭。ADR-012。

## Done when

- G12–G16；真机：alice 再问时确认单显示「历史选择」与日期；bob、finance 空间看不到；改映射后
  不再沿用；`--yes` 不预填。
