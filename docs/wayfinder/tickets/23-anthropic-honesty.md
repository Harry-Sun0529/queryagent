---
status: open
type: task
blocked_by: []
claimed_by:
---
# T23 — Anthropic 后端：把声明降到证据的水平

## Question
README 宣称"两个 provider"，但 Anthropic 后端**从未对真实 API 调用过**，
而且上一轮才发现它连当前 SDK 都不兼容。拿不到 key 就无法验证——那么正确
的做法是**改声明**，不是留着让读者默认它被验证过。

## Work
- README / CONTEXT 明确标注：Anthropic 后端有契约级测试，但**未经真机
  验证**；DeepSeek 路径是被真机与评测覆盖的那条。
- 说明 temperature 在该后端不生效（SDK 1.x 已移除）。
- 若将来拿到 key，验证清单写在 ticket 里备用。

## Done when
- 文档里再没有"未经验证却读起来像已验证"的声明。
