---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
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

## Resolution (closed 2026-08-22)

- README 新增「How far each backend is verified」注记：**所有已发布的数字、
  三方言真机冒烟、失因分析，全部经由 OpenAI 兼容后端 + DeepSeek 产出**；
  Anthropic 后端只有契约级测试、**从未对真实 API 调用过**，且直到 CI 抓到
  之前它对 anthropic 1.x 是坏的。
- Features 段的「两个 provider」补上「两者的验证程度不同」。
- CONTEXT 的 seam 表标注哪条路径被验证过。
- temperature 在该后端不生效一并写明（SDK 已移除该参数）。

**这条 ticket 的终点是改声明，不是验证通过**——拿不到 key 就不该让读者
默认它被验证过。
