---
status: closed
type: task
blocked_by: [01]
claimed_by: fable-session
---
# T3 — 成本、延迟与缓存命中进 eval 报告

## Question
现在报告只有五个正确性指标，答不了「你的 agent 每个问题多少钱多久」。

## Work
- `queryagent/evals/cost.py`：DeepSeek 分档定价表（v4-flash / v4-pro ×
  cache hit / miss；输出单价单列）。定价随时会变 → 表里标注抓取日期与
  来源 URL，并支持 config 覆盖。**peak/off-peak 不做自动判定**（依赖
  UTC 时段，易错且不可复现），统一按 peak 价报，报告里注明「上限估计」。
- runner 聚合每个 case 的 tokens / cost / wall-clock，报告新增
  「平均每题 token / 成本 / 耗时 / prompt 缓存命中率」。
- 缓存命中率单列——系统提示在多轮间不变，这是本架构的真实成本杠杆。

## Seams (tdd)
1. 定价计算：给定 usage 与模型名，算出成本（含 cache 分档）。
2. runner 聚合：scripted 事件流断言汇总数字。

## Done when
- 测试绿；一次自建集 eval 报告里出现四个新指标且数值合理。

## Resolution (closed 2026-08-19)

- `queryagent/evals/cost.py`：DeepSeek 分档定价（cache hit / miss / output），
  抓取日期与来源 URL 写在模块 docstring；未知模型返回 `None` 而不是猜，
  报告显示 n/a —— 过期价目表永远不会悄悄编出数字。
- **peak/off-peak 不做自动判定**：那要依赖调用时刻的 UTC 时间，会让报告
  不可复现且无分析价值。统一按 peak 价计，标注为「上限估计」。
- `TokenTotals` 可相加、自带 `cache_hit_rate`；runner 从 UsageEvent 累计，
  报告新增四行：每题 token、缓存命中率、每题耗时、每题成本上限。
- 10 个新测试（7 定价 + 3 runner 聚合）。
