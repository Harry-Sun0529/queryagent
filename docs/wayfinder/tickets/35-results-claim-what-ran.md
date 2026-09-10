---
status: open
type: task
blocked_by: [33, 34]
claimed_by:
---
# T35 — 结果只声称已执行的，空结果如实说，真机验收

## Question

区间进了 SQL 之后，结果行与免责说明要跟着改；区间内没有记录时不能显示成 0 或裸 NULL。

## Work

- 结果行列出选定口径与统计区间（P8）；未限定区间时明写（P9）；空聚合明说（P10）。
- 演示映射改为结构化；端到端测试改为区间内的真实数字。
- 文档：README / CHANGELOG / CONTEXT / 方案实施结果 / prompt-log；ADR-008 记录 C01。

## Done when

- 真机：「上个月新增用户」执行 SQL 带区间条件，数字与手写参照一致；结果行不再为区间免责。
