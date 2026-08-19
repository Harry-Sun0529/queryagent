---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T18 — `--resume` 必须校验运行签名

## Question
`--resume` 会无条件复用 `<output>.partial.jsonl` 里的结果。如果上一次用的是
**另一个模型**（或另一份 cases / 另一个 max-turns），复用会把两次运行的结果
混进同一份报告——产出一个没人能解释的数字。这正是本轮一直在防的那类问题：
**不可信的数字比没有数字更糟**。

不带 `--resume` 的情况已经处理（删旧日志）；有 `--resume` 时缺校验。

## Work
在日志首行写入运行签名（model / backend / cases 来源 / max_turns），
`--resume` 时比对：不一致则拒绝复用并说明差异，而不是静默混合。

## Seams (tdd)
1. 签名一致 → 复用。
2. 签名不一致（换模型）→ 拒绝并提示，不产出混合报告。

## Done when
- 两个 seam 测试绿。

## Resolution (closed 2026-08-20)

- 日志首行写运行签名（backend/model · cases 文件名 · max_turns）；
  `--resume` 时比对，不一致则拒绝并打印双方签名，退出码 2。
- **空签名不触发拦截**：只有真正的运行才声明签名，读日志的工具不该被挡。
- 2 个 seam 测试（换模型被拒 / 同配置可续）。
- 附带把增量落盘测试的断言从「文件行数」改成「恢复出的结果集合」——
  按行数断言会被任何格式变化误伤，按结果断言才表达真正的意图。
