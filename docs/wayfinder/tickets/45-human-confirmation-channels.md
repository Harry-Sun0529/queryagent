---
status: open
type: task
blocked_by: [44]
claimed_by:
---
# T45 — 人的确认通道：本地确认页与终端确认

## Question

MCP 不暴露确认之后，人要在哪里确认？本地网页服务又带来 CSRF、DNS rebinding、XSS 三类典型漏洞。

## Work

- `queryagent web`：标准库 `http.server`，只监听 127.0.0.1；一次性登录链接换 HttpOnly +
  SameSite=Strict 会话；POST 校验 Host、Origin、绑定版本与哈希的表单令牌；所有输出转义。
- 页面：待确认列表、草案页（确认单与补充表单）、确认；Agent 代填的规则高亮。
- 终端：`queryagent drafts`、`queryagent confirm <draft_id>`（砍掉网页时的退路）。
- 确认记录新增 `channel`（cli / web）；`store.pending_drafts`。
- SECURITY 写明诚实边界：同一 OS 用户下有任意 shell 的 Agent 能绕过任何本地确认。

## Done when

- H6–H9；真机：浏览器手测一遍；curl 负面测试（伪造 Host、缺令牌、跨站 Origin、含 `<script>`
  的文档）全部拒绝且状态不变。
