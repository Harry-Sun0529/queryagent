---
status: open
type: task
blocked_by: [02, 04, 05, 07, 08]
claimed_by:
---
# T9 — 收口

## Work
- README：Evaluation 章节重写（dev/test 双集 × 强弱双模型 × 成本延迟）；
  新增可观测性与 trace 隐私说明。
- CHANGELOG 0.3.0；版本号 bump。
- **ADR-004 改写**为记录 dev/test 切分（不是推翻，是升级：原则不变，
  纪律更严）。
- **新增 ADR-005**：trace 默认开启的取舍（可观测性 vs 隐私，及为何用
  gitignore 而非仅文档提醒兜底）。
- SECURITY.md 补 trace 落盘的数据面风险。
- 同步更新桌面《QueryAgent精读解析.md》到 v0.3.0（新增 UsageEvent、
  conversation 参数、trace/replay）。
- 打 tag v0.3.0，**不推送**——等人工 review 找 bug。

## Done when
- `make test` 全绿；文档无过时描述；tag 已打但远端无变化。
