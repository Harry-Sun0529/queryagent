---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T13 — 会话折叠黑盒测试与 agent_sql 可读性

## Question
多轮会话记忆只有真机验证，没有自动化测试；`run_case` 里
`next(iter(matched), successful[-1])` 逻辑正确但可读性差。

## Work
- 黑盒测试（seam = `main(["chat"])`）：伪造 stdin 与后端，断言**第二轮
  发给模型的消息里带着第一轮的问答**。与已有的 ContextBuilder 单测形成
  差分诊断（外层红+内层绿 ⇒ bug 在折叠层）。
- 追问轮的用户补充说明是否进入 conversation，一并钉死（当前刻意进入）。
- `run_case` 的 matched 集合改为显式的 `matched_sql: str | None`。

## Seams (tdd)
1. `main(["chat"])` 两轮问答 → 第二次 complete 的 messages 含第一轮内容。
2. 追问轮 → 存入 conversation 的 user 文本包含补充说明。

## Done when
- 两个 seam 测试绿；重构后全套测试不变绿。

## Resolution (closed 2026-08-19)

- 两个黑盒测试（seam = `main(["chat"])`）：跟进轮的消息里必须带着上一轮
  的问题与答案；首轮不得凭空带 conversation。
- **两个测试直接就是绿的**（该行为本来正确），所以做了一次**变异验证**：
  故意注释掉折叠语句 → 跟进轮测试变红；恢复 → 变绿。证明不是空测试。
  这类补测叫特征化测试，不是 TDD 循环，如实标注。
- 与已有的 ContextBuilder 单测构成差分诊断：外层红+内层绿 ⇒ bug 在折叠层。
- `run_case` 的 `matched: set[str]` 改为 `matched_sql: str | None`，
  `passed` 由它派生，`next(iter(matched), ...)` 那行消失。
