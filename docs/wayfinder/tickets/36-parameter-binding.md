---
status: closed
type: task
blocked_by: []
claimed_by: opus-session-2026-09-10
---
# T36 — 统计区间的日期以绑定参数进入查询

## Question

ADR-008 用类型化编译顶住了 1C，并写明值的种类一多就该换成参数绑定。分组（T38）与之后的
维度取值过滤都会带来新的值；字面量格式按方言各是一份兼容承诺，1C 已经因此漏过每个区间的
第一天。现在把日期改为绑定参数。

## Work

- `Connector.execute(..., params=())`；SQL 统一用 `?` 占位。SQLite 原生；MySQL 转 `%s`、
  ClickHouse 转 `%(pN)s`，传参时非占位词元里的 `%` 一律成对（两个驱动都是 `query % 参数`）。
- 编译器输出 `CompiledQuery(sql, params)`；执行器、`QueryRun` 与存储带上 `params`。
- 确认后展示的 SQL 与参数分开列出。
- ADR-009 取代 ADR-008。

## Done when

- F1–F3：编译出的 SQL 文本里没有日期字面量；三方言结果与原生月份函数一致；维护者片段里的
  `%` 在传参时语义不变；不传参时连接器行为不变。

## Resolution（2026-09-10）

- 占位符翻译放在连接器一侧（`connectors/params.py`），按 sqlparse 词元改写：字面量里的 `?`
  与 `%` 保持原样，真实占位符改成驱动写法，其余 `%` 成对。离线测试把翻译结果真的过一遍
  `%` 格式化，断言驱动发出的就是维护者写的语句。
- 值按 ISO 字符串绑定：sqlite3 默认的 date 适配器已弃用，而且驱动渲染出的文本与 1C 相同，
  三方言对照结果不变（MySQL `DATE_FORMAT`、ClickHouse `toYYYYMM` 各一条，另各加一条
  `LIKE '%rgan%'` 与绑定值同句的 F2 测试）。
- `QueryRun.params` 落盘；v0.7 的状态文件打开时自动补列（有测试从旧表结构起步）。
- 真机：「上个月新增用户」注册口径仍为 5812，SQL 里只剩 `?`，参数单列一行。
- 诚实边界写进 ADR-009：MySQL/ClickHouse 上的"绑定"是驱动的客户端转义，不是服务端预编译。
