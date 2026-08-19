---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T10 — 支持 DeepSeek 思考模式（reasoning_content 回传）

## Question
显式使用 `deepseek-v4-flash` 时，**第二轮工具调用必然 HTTP 400**：
`The reasoning_content in the thinking mode must be passed back to the API.`
自建集自修正后通过率从 17-18/18 掉到 10-11/18 —— 由 T5 的双模型跑分暴露。

## Root cause
v4 系列是思考模型，assistant 消息含 `reasoning_content`（与 `content`、
`tool_calls` 并列）。协议要求把它随对话回传，我们的 `_convert_message`
只回传了 content 与 tool_calls，于是第二轮请求被拒。

旧基线用 `deepseek-chat` 别名（未启用思考模式）所以从未暴露 —— 别名掩盖了
一个真实的协议缺口。

## Work
- `ModelResponse.reasoning` / `Message.reasoning`（默认空串，向后兼容）。
- OpenAI 后端解析 `reasoning_content`，并在 assistant 消息中回传。
- `run_agent` 把 reasoning 存进 history 的 assistant 消息。

## Seams (tdd)
1. 后端解析 reasoning_content。
2. 回传：带 reasoning 的 assistant 消息序列化后含 `reasoning_content`。
3. `run_agent`：多轮对话中 reasoning 被带回后端。

## Done when
- 三个 seam 测试绿；真机对 v4-flash 与 v4-pro 各跑一次多轮问题不再 400；
  自建集恢复到铁基线水平。

## Resolution (closed 2026-08-19)

- `Message.reasoning` / `ModelResponse.reasoning`（默认空串，向后兼容）；
  OpenAI 后端解析 `reasoning_content`，并在带 tool_calls 的 assistant
  消息里回传；`run_agent` 把它存进 history。
- 3 个 seam 测试 + 1 个 agent 测试；`make test` 210 全绿。
- 真机：v4-flash 与 v4-pro 的两轮工具调用均恢复正常。

**这条是本轮最有价值的发现**：`deepseek-chat` 别名（未开思考模式）掩盖了
一个真实的协议缺口，一旦显式指定 v4 模型，**第二轮工具调用必然失败**。
它是被 eval 的跑分回归抓出来的 —— 正是「评测体系存在的意义」的实证：
单元测试全绿、单轮 `ask` 正常，只有多轮跑分才暴露。
