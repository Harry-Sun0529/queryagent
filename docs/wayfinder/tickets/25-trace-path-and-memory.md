---
status: open
type: task
blocked_by: []
claimed_by:
---
# T25 — trace 落点与长会话内存

## Question
两个小缺陷：trace 目录是相对 CWD 的，同一个用户换个目录运行，trace 就散落
在各处、`replay` 找不到；chat 的 `conversation` 列表随会话无界增长（提示
侧有裁剪，内存侧没有）。

## Work
- trace 目录支持 config 显式配置；未配置时仍相对 CWD，但启动提示里打印
  绝对路径，让用户知道东西在哪。
- `conversation` 保留最近 N 轮（N 可配），与 context 裁剪的方向一致。

## Seams (tdd)
1. config 指定 trace 目录时写到该处。
2. 会话超过 N 轮后，最旧的轮次从内存中移除。

## Done when
- 两个 seam 测试绿。
