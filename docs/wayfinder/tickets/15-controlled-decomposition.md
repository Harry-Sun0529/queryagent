---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T15 — 受控分解：83% → 61-72% 的归因

## Question
v0.2.0 README 报首答率 83%，v0.3.0 报 61-72%。两者差在**代码**还是
**模型配置（思考模式）**？不分解就无法回答「你的代码是不是把指标做差了」。

## Work
在**自建集**上跑两格（每格 2 次取区间）：
- 格 A：v0.2.0 代码 + `deepseek-chat`（关思考）← 复现 v0.2.0 测量条件
- 格 B：v0.3.0 代码 + `deepseek-chat`（关思考）
已有格 C：v0.3.0 代码 + `deepseek-v4-flash`（开思考）= 61-72%
A→B = 代码贡献，B→C = 思考模式贡献。
用 git worktree 取出 v0.2.0 代码，独立 venv 避免污染当前环境。

## Done when
- 三格数字齐备，能一句话说清落差的归因；报告落 `eval/results/`。
- 若结论对我们不利，按 Q4 裁定**如实发布**并解释为何保留该改动。

## Resolution (closed 2026-08-19)

报告见 [eval/results/version-decomposition.md](../../../eval/results/version-decomposition.md)。

**A→B（只变代码）首次 +5pp、自修正后 +5-11pp ⇒ 代码是正贡献；
B→C（只变模型配置）首次 83%→61-78%、自修正后不变 ⇒ 已发布的下降
全部来自开启思考模式。** 按 Q4 的预案本来准备「结果不利也如实发布」，
实际结果有利，但报告里仍如实标注了一处局限：格 A 用的是今天的用例文件，
不是对历史 83% 的复现（复现需连用例一起回滚，那会同时变两个因素）。

附带发现：思考模式引入方差——A、B 两跑完全一致，C 在 11-14 间波动。
