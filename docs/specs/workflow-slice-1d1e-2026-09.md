# 切片 1D/1E：预算、确认前新鲜度、历史沿用、取值过滤

日期：2026-09-11。状态：计划（验收标准在实现前固定）。承接 v0.8.0（`885e30b`），
铁基线 694 passed / 1 skipped。

## 1. 为什么做这一刀

交接文档把阶段 1 拆成 1A–1E，其中 1A–1C 已随 v0.6–v0.8 落地。剩下两块写得很具体：1D
「可复用历史选择但不是团队标准」；1E「总查询次数/时间/并发预算由维护者配置，不可被模型或
用户提高」，以及「探索必须只读且有总预算，行数上限不等于扫描上限」。真机上对应四处答不上来：

1. **没有总量上限。** 单条查询有超时和行数上限，但一个人一天能跑多少、同时能跑几条、agent
   一次能探索多少条，都没有上限；SECURITY.md 至今写着总预算与准入控制 "still do not" 存在。
   v1.0 让别的 Agent 能调用之后，这是真实风险。行数上限也不限制扫描量。
2. **不完整月只能在结果上说。** 演示数据止于 08-22，9 月问「上个月」要确认并执行后才知道只
   覆盖到 08-22。v0.8 把这写成了有意识的代价：确认前不查询是 I2。本切片按上一轮的讨论收窄
   I2，并提供不需要查询的另一条路（维护者声明的更新节奏）。
3. **每次都从零选口径。** alice 昨天选了首单口径，今天再问同一个指标还要再选一遍。
4. **「广告渠道的新增用户」做不了。** 只能分组，不能过滤；v0.8 的参数绑定为它铺好了路。

## 2. 已定的设计取舍

| 编号 | 取舍 | 理由 |
|---|---|---|
| E01 | 预算只写在 `config.yaml` 的 `budget:` 段；没有任何 CLI 参数、MCP 参数、口径规则或文档能提高它。段不存在就不启用，行为与 v0.8 完全一致 | 交接文档原话：不可被模型或用户提高。存在即开关，与 `knowledge:` 同理，回退可以写成测试 |
| E02 | 预算作用于面向使用者的入口：`flow` / `ask` / `chat`（v1.0 加上 `mcp`）；不作用于 `eval` | eval 是维护者的测量工具，自带并发与熔断；受每日额度限制会让基准跑不完 |
| E03 | 预算项：每次请求语句数、每人每天执行次数、每人每天累计执行秒数、同一状态文件上的并发数，以及可选的扫描行数上限。扫描上限只有 ClickHouse 能由引擎强制（`max_rows_to_read`），在其他方言上配置它，加载时直接拒绝 | 写了却不生效的上限是假话。只有一个方言做得到真正的扫描上限，就照实只支持这一个 |
| E04 | flow 的准入放在确认、证据、编译都通过之后、占用幂等键之前；一次执行按「探测 + 业务查询」两条预占。被拒绝时零 SQL，幂等键不被消耗 | 与 1A 的顺序原则一致：越早的拒绝，副作用越少 |
| E05 | 并发用存储里带到期时间的租约（单条超时 + 余量），`BEGIN IMMEDIATE` 保证原子，跨进程有效；崩溃留下的租约到期自动释放 | 多个 CLI 进程可能共用一个状态文件，只在进程内计数挡不住 |
| E06 | 超限时说清卡在哪一项、何时恢复。每日额度用尽退出码 2，并发已满退出码 75 | ADR-006：前者是环境/输入，后者是稍后可重试 |
| E07 | agent 路径每一次 `execute_sql` 走同一本账；超限返回工具错误 Observation，不抛异常，模型据此收尾 | seam 规则：工具失败返回 Observation，只有 SafetyViolation 才抛 |
| E08 | I2 收窄为「确认前不执行任何业务查询」。唯一例外是编译器生成的 `SELECT MAX(time_column) FROM source`，而且只在维护者设 `workflow.freshness_before_confirm: probe` 时才允许；默认 `declared`，确认前零查询 | 默认保持 I2 原样，放宽是维护者的主动选择；写进 ADR-010 |
| E09 | 确认前探测：短超时（默认 2s）；按（表，时间列）缓存在存储里（默认 10 分钟）；计入预算；只作参考，不进内容哈希，确认单标「探测于 HH:MM，仅供参考」；执行时照旧重新探测，结果上的覆盖说明以执行时为准 | 探测值会变。进了哈希，数据一更新确认就失效；执行时再探一次，结果说的才是真话 |
| E10 | 映射可以声明 `freshness: {lag_days: N}`（T+N）：确认单不查库就能给出预期最新日期，并提示区间末尾可能不完整；执行后实测比声明更旧时，结果点名「比声明的更新节奏滞后 K 天」 | 零查询的提前提醒；顺带能发现 ETL 延迟 |
| E11 | 历史选择是提议，不是标准：新来源 `RuleSource.HISTORY`（「历史选择」），写明来自哪天的哪次执行；进哈希；只按同一人 + 同一业务空间取用 | 不跨人，就不会变成隐形的团队口径 |
| E12 | 历史只填缺口：沿用口径（variant）、文档分歧里采用的写法、用户补过的缺口；不沿用统计区间与分组。文档依据已经预选了口径时历史不覆盖它，不一致时确认单点名「你上次选的是 X」 | 文档是事实，历史是偏好；区间与分组描述的是这一次的问题 |
| E13 | 不沿用的条件，任一即可：映射指纹变了；所引文档复查不再 OK；该选项在本次草案里不存在（候选键 + 摘要 + 出处）；超过 `workflow.history_max_age_days`（默认 90）。因文档失效而不沿用时不说是哪份 | 映射改了，同一个口径名底下的 SQL 可能已经不同；不点名沿用 1B 的单一措辞 |
| E14 | 没人看确认单的通道不预填历史：`--yes` 时不预填，缺口照旧要显式参数；`--no-history` 显式关闭 | 否则一个带 `--yes` 的脚本会从「遇到缺口就取消」变成「静默沿用上次口径」 |
| E15 | 取值过滤：维度声明封闭取值 `values: {ads: [广告, 付费投放]}`；新规则键 `filter`（`dim:channel=ads`），只来自用户（问题字样或 `--filter`），进哈希，编译为 `AND (col = ?)` 绑定参数；认不出的取值列为缺口并给出可选值；一次一个维度 | 绑定防得住注入，防不住「一个不存在的值查出 0，冒充业务为 0」 |

## 3. 对接方必读

- 配置：

  ```yaml
  budget:                          # 可选；不写就与 v0.8 完全一致
    max_queries_per_request: 3     # 一次确认执行（含探测）或一次 ask 探索
    max_runs_per_day: 50           # 每个主体每天，按 workflow.timezone 计日
    max_query_seconds_per_day: 600 # 客户端计时，不是服务器 CPU 时间
    max_concurrent: 2              # 同一状态文件上同时执行的查询
    max_rows_scanned: 50000000     # 仅 ClickHouse；其他方言配置了会在加载时报错
  workflow:
    freshness_before_confirm: declared   # declared | probe | off
    freshness_probe_timeout_s: 2
    freshness_cache_minutes: 10
    history_max_age_days: 90
  ```

- 映射文件：维度可加 `values:`（取值键 → 问题里的说法），结构化映射可加
  `freshness: {lag_days: N}`。
- `QueryRun` 新增 `started_at`、`elapsed_ms`、`mapping_fingerprint`，沿用 `_LATER_RUN_COLUMNS`
  自动补列；新表 `budget_leases`、`budget_ledger`、`freshness_cache` 在同一状态文件里。
- `RuleSource.HISTORY` 是单向变更：v0.8 打不开含历史规则的草案；v0.8 写下的草案在 v0.9 可读。
- 新错误 `BudgetExceeded(WorkflowError)`，带 `item` 与 `retry_after`。新 CLI 参数 `--filter`、
  `--no-history`。`COMPILED_RULE_KEYS` 加入 `filter`；文档抽取的允许键不变。

## 4. 内部设计

| 票 | 模块与复用 |
|---|---|
| T40 | 新 `queryagent/budget.py`（agent 路径也用，不放 `workflow/`）：`SqliteBudgetLedger.admit(subject, queries, now) -> Lease`（上下文管理器，`record(elapsed)`，退出释放），带 `busy_timeout`。flow 顺序 `compile → admit → claim_run → probe → query → record`，幂等重放时释放租约。agent 路径用 `BudgetedConnector` 包住连接器交给 `make_default_tools`。ClickHouse 连接器按配置传 `max_rows_to_read`。`cli._explain` 映射退出码 |
| T41 | 新 `workflow/freshness.py`；`mappings._parse_structured` 读 `freshness:`；`compiler.freshness_probes`（口径未定时每个候选各一条，按表去重）；`QueryWorkflow.freshness_advisory(actor, draft)` 按需计算、不落草案、不进哈希；`render_coverage` 加「滞后」说明 |
| T42 | 新 `workflow/history.py`：`HistoryDraftBuilder` 包在 `CompositeDraftBuilder` 外，只填仍缺的键。`store.recent_confirmed(...)` 由 drafts ⋈ confirmations ⋈ runs 派生，不另建历史表；`mappings.mapping_fingerprint(entry)` 执行时写到 run 上；文档复查复用 `RefChecker.check_refs` 与 `EvidenceRef.parse`；`--yes` / `--no-history` 在装配时决定是否套这一层 |
| T43 | `grouping.Dimension.values`；`find_filter` / `parse_filter` 要求维度语境（「X渠道」「渠道为X」）；`FILTER_RULE_KEY`；`compiler._compose` 追加 `(col = ?)`，`to_pyformat` 无需改；探测仍查整表 |

## 5. 不变量与验收

| 编号 | 不变量 |
|---|---|
| G1 | 未配置 `budget:` 时，四条入口的行为与 v0.8 一致 |
| G2 | 预算只在构造时从配置读入；没有 CLI / MCP 参数、规则或文档路径能改变它（结构测试） |
| G3 | flow 超限：零 SQL、幂等键未被消耗、runs 表不新增；消息点名超出项 |
| G4 | 并发上限跨进程成立（两个存储实例同一文件）；崩溃留下的租约到期释放 |
| G5 | agent 路径超限返回工具错误而非抛出；单个问题执行的语句数不超过上限 |
| G6 | 非 ClickHouse 方言配置 `max_rows_scanned`，加载即拒绝 |
| G7 | ClickHouse 扫描上限由引擎强制：超过即失败，报「扫描上限」，不是超时 |
| G8 | `declared` / `off` 模式下，确认前执行计数为 0 |
| G9 | `probe` 模式下，确认前执行的语句全部等于编译器生成的探测；同一表缓存期内只探一次；探测计入预算 |
| G10 | 确认前探测值不进哈希：变化不使确认失效；执行时重新探测，结果以执行时为准 |
| G11 | 声明 T+N 的映射：确认单零查询给出预期最新日期与不完整提示；实测滞后时结果点名 |
| G12 | 历史选择显示为「历史选择」并写明日期，进哈希；绝不显示成「本次约定」或「文档依据」 |
| G13 | 历史不跨主体、不跨业务空间 |
| G14 | 映射指纹变化、所引文档撤权或变更、选项已不存在、超龄 → 不沿用；因撤权不沿用时不泄露文档名 |
| G15 | 历史只填缺口，不覆盖文档依据与问题字样；不沿用区间与分组 |
| G16 | `--yes`、`--no-history` 下不预填；v0.8 写的草案在 v0.9 可读 |
| G17 | 取值过滤以绑定参数进入 SQL；三方言与各自原生过滤一致；与分组同用时逐组合计与不分组一致 |
| G18 | 未声明的取值、声明之外的值 → 缺口并给出可选值，零 SQL；文档无法产生 `filter` |

## 6. 票

| 票 | 内容 | 依赖 |
|---|---|---|
| T40 | 统一预算与准入：配置、账本与租约、flow 准入、agent 路径、ClickHouse 扫描上限、退出码、ADR-011 | — |
| T41 | 确认前新鲜度：声明的更新节奏、可选探测与缓存、确认单提示、结果侧滞后说明、ADR-010 | T40 |
| T42 | 历史沿用：`RuleSource.HISTORY`、由存储派生、四个失效条件、`--yes` / `--no-history`、ADR-012 | — |
| T43 | 取值过滤（可砍）：`values:`、`filter` 规则、三方言编译 | — |

顺序 T40 → T41 → T42 → T43。每张票独立提交、提交前全量通过；整片完成、真机验证后一次推送。
砍单顺序：先砍 T43，再砍 T41 的 `probe` 模式（保留 `declared`）。

## 7. 风险与回滚

- 回滚点 `v0.8.0`。不写 `budget:`、`freshness_before_confirm: declared`、`--no-history`、映射里
  不写 `values:`，行为就回到 v0.8；每张票可单独 revert。
- 改的是信任属性（I2）：默认不变、维护者主动开启、ADR-010 写明新表述、G8/G9 用确定性测试钉住
  「确认前只可能跑探测」。
- SQLite 写竞争：WAL + `BEGIN IMMEDIATE` + `busy_timeout`；多副本仍不在承诺内。
- 执行秒数是客户端计时，含网络；「一天」按 `workflow.timezone` 计。
- 历史让人偷懒：确认单标明来源与日期、与文档不一致时点名、`--yes` 不预填、确认这一步不变。
- 取值误判（「广告费」「推荐语」）：要求维度语境，专门写误判测试；过滤条件显示在确认单上。

## 8. 明确不承诺

MySQL / SQLite 的服务器扫描、CPU、内存上限（只有超时）；按 EXPLAIN 估算成本做准入；团队共享
的标准口径；跨设备、跨人的历史；数据完整性（仍只报最新记录日期与声明的节奏）；多维过滤、IN
列表、范围过滤、自由文本取值；多副本共享账本。

## 9. 真机验证

- 预算：`max_runs_per_day: 2` 跑三次 flow，第三次退出码 2、runs 表计数不变；`max_concurrent: 1`
  同时发两个慢查询，第二个退出码 75；ClickHouse 上很小的 `max_rows_scanned` 由引擎拒绝；`ask`
  配 `max_queries_per_request: 1` 接真实 DeepSeek，跑一条后带预算提示收尾。
- 新鲜度：声明 T+1 后问「本月成交额」，确认单零查询给出预期，执行后点名滞后；`probe` 模式下
  确认单出现「库中最新记录 2026-08-22（探测于…）」，缓存期内再问不再探测。
- 历史：alice 选首单口径后再问，确认单显示「历史选择」及日期；bob、finance 空间看不到；改映射
  的 where 后不再沿用；`--yes` 不预填。
- 取值过滤：「上个月广告渠道的新增用户」= 2307，与按渠道分组的 ads 一致；加「每天」后逐日合计
  等于 2307；三方言对照。
