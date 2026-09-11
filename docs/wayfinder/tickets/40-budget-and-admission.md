---
status: closed
type: task
blocked_by: []
claimed_by: opus-session-2026-09-11
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

## Resolution（2026-09-11）

- 预算只写在 `config.yaml` 的 `budget:` 段，不写就与 v0.8 一致。账本放在 workflow 状态文件里：
  按主体、按业务日的计数，加带到期时间的并发租约，`BEGIN IMMEDIATE` 原子准入。
- 每日上限按**语句**计（`max_queries_per_day`，含探测），不是方案原稿的 `max_runs_per_day`：
  flow 与 agent 路径用同一个单位，才能共用一本账。
- flow 的顺序：先按幂等键找已有的 run，再准入、占键、探测、查询。被拒时零 SQL、键未消耗。
  **实施中发现**：先准入会让额度只剩一条时的重放被拒，而重放什么都不执行。
- agent 路径：`BudgetedConnector` 逐条准入；超限回到模型的是错误 Observation（写明"重试不会
  成功"），模型据此用已有结果作答。
- `BudgetExceeded` 继承 `QueryAgentError`，不是方案写的 `WorkflowError`：agent 路径也会抛它，
  不经过 workflow 层。退出码按 `retryable` 分；并发满时，消息写明最迟多久空出一个（review 补）。
- 扫描上限走 ClickHouse 引擎的 `max_rows_to_read`，错误码 158 改写成「超过扫描上限」；在其他
  方言上配置，加载时拒绝。
- 真机：
  - SQLite 演示库：alice 第二次 flow 被拒（退出码 2，写明次日 00:00 恢复、只有维护者能调整），
    bob 不受影响；
  - MySQL：两个并发 flow（`max_concurrent: 1`，查询带 `SLEEP(3)`），第二个退出码 75，结束后
    租约表为空；
  - ClickHouse：flow 被引擎拒绝（要读 5 万行，上限 1000）；
  - `ask` 接 DeepSeek：第二条语句收到预算 Observation，模型以第一条的结果作答并说明缺了什么。
- 写明的代价（ADR-011）：秒数由客户端计时，最后一条可能超出一个超时；每日额度只和身份一样强，
  本地 `--subject` 可以换人，要按人限额需要宿主传入身份（v1.0）。
