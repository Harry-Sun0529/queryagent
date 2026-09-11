---
status: open
type: task
blocked_by: [40, 41, 42]
claimed_by:
---
# T44 — MCP 适配器：Agent 能准备、能执行，不能确认

## Question

MCP 能让 Claude Code 这类宿主直接调用，但宿主里的 Agent 自己就能「点确认」。怎样开放能力而
不开放确认？

## Work

- 手写 stdio JSON-RPC（固定协议版本；`initialize` / `tools/list` / `tools/call` / `ping`），零新
  依赖；stdout 只放协议帧。
- 工具：`list_metrics` / `prepare_query` / `amend_query` / `query_status` / `execute_query`；没有
  确认工具；身份只来自 `queryagent mcp --subject --workspace`。
- `QueryWorkflow.execute_confirmed(actor, draft_id, idempotency_key)`：服务端找当前版本上由人
  产生的确认。
- `RuleSource.AGENT`（「Agent 代填」）；`workflow/wiring.py` 抽出组装代码，CLI 与 MCP 共用。
- ADR-013。

## Done when

- H1–H5；真机：Claude Code 接入后问「上个月新增用户多少」，Agent 执行失败并请人确认，人确认后
  得到 5812；让 Agent「替我确认」无工具可用，确认表为空。
