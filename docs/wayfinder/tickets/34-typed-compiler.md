---
status: closed
type: task
blocked_by: [32]
claimed_by: opus-session-2026-09-10
---
# T34 — 结构化映射与类型化编译

## Question

怎样让区间进 SQL，同时保证用户原话进不了 SQL，且整条 SQL 的旧映射不会静默丢掉区间？

## Work

- 映射支持 `from` / `measure` / `time_column` / `where` / `label`；旧 `sql:` 保留。
- 编译器按方言引用别名（MySQL 反引号，其余双引号），区间编成半开条件。
- `sql:` 映射遇到区间 → `MappingNotFound`（"该映射无法施加统计区间"）。
- `from` / `time_column` 加载时做标识符校验。

## Done when

- P5：SQLite / MySQL / ClickHouse 上编译结果与手写参照查询一致（集成测试）。
- P6、P7 有测试。

## Resolution（2026-09-10）

映射支持结构化条目（`from` / `measure` / `label` / `time_column` / `where`），与 1A
的整条 `sql:` 并存。编译器把已确认的区间编成半开条件
`time_column >= 'start 00:00:00' AND time_column < 'end+1 00:00:00'`。

**P5 在三种方言上跑过，参照查询用各方言自己的日期函数**，避免拿同一条 SQL 验证自己：
SQLite 用围绕月边界构造的行（首日零点在内、末日 23:59:59 在内、次月零点在外）；
MySQL 对照 `DATE_FORMAT(created_at, '%Y-%m')`；ClickHouse 对照 `toYYYYMM(created_at)`
（字符串边界对 `DateTime` 列）。月份取自库里数据，不写死——演示数据按建库当天生成。

- **P6**：整条 `sql:` 映射遇到区间 → 拒绝，并说明不会忽略区间去跑全量；没有区间时照旧可用。
- **P7**：日期只能经 `Period.decode` 以 `date` 对象进入语句；非规范的区间值、带引号的
  口径键、文档与本次约定里写着 SQL 的规则文字，都到不了 SQL。
- 维护者 `where` 片段一律加括号：不加的话，片段里的 `OR` 会越过旁边的区间条件，把
  所有时间的已支付订单都数进来——有一条执行测试钉着。
- 别名按方言加引号（MySQL 反引号，其余双引号）；`label` 加载时拒绝引号字符，所以
  引号包不住它的情况不存在。

没有做参数绑定（C01）：进入语句的值只有维护者片段与 `date` 对象两类，扩展 Connector
协议另立一刀。
