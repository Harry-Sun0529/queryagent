---
status: open
type: task
blocked_by: []
claimed_by:
---
# T40 — 统一预算与准入

## Question

单条查询有超时和行数上限，但一个人一天能跑多少、同时能跑几条、agent 一次能探索多少条都没有
上限；行数上限也不限制扫描量。交接文档要求这些上限由维护者配置、模型与用户都不能提高。

## Work

- `config.yaml` 新增可选 `budget:` 段：每次请求语句数、每人每天次数、每人每天累计秒数、并发、
  ClickHouse 扫描行数上限；在其他方言上配置扫描上限，加载即拒绝。
- 新模块 `queryagent/budget.py`：`SqliteBudgetLedger`，存储里带到期时间的租约与每日账本，
  `BEGIN IMMEDIATE` 保证跨进程原子。
- flow：`compile → admit → claim_run → probe → query → record`；拒绝时零 SQL、幂等键不被消耗；
  幂等重放释放租约。
- agent 路径：`BudgetedConnector` 包住连接器，超限返回工具错误 Observation。
- `BudgetExceeded`：每日额度退出码 2，并发退出码 75，消息点名超出项与恢复时间。
- ADR-011。

## Done when

- G1–G7；真机：三次 flow 第三次被拒且 runs 表不变；并发第二个退出码 75；ClickHouse 扫描上限
  由引擎拒绝；`ask` 在语句上限处带预算提示收尾。
