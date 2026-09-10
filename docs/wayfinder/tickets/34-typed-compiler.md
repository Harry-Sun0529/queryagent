---
status: open
type: task
blocked_by: [32]
claimed_by:
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
