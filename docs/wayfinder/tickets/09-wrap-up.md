---
status: closed
type: task
blocked_by: [02, 04, 05, 07, 08]
claimed_by: fable-session
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

## Resolution (closed 2026-08-19)

- README：Evaluation 章节重写（双模型区间 + dev/test 双集 + 成本延迟缓存），
  Features 补可观测性并把终止条件订正为五种。
- CHANGELOG 0.3.0；版本号 bump；SECURITY.md 新增「Traces on disk」段。
- ADR-004 改写为记录 dev/test 切分（原则不变，纪律更严）；新增 ADR-005
  记录 trace 默认开启的取舍与被否决的部分脱敏方案。
- eval/README 更新为双集纪律。
- 桌面《QueryAgent精读解析.md》补 v0.2.0-v0.3.0 增量八节。
- **按人类指示：打 tag 但不推送**，等人工 review 找 bug 后再发布。
