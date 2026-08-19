---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T1 — usage 透传与 UsageEvent

## Question
后续所有度量（成本、延迟、缓存命中）都需要模型调用的 usage，但
`ModelResponse` 不携带它、两个 backend 也没解析。如何在不破坏 §二 稳定
接口的前提下把 usage 送进事件流？

## Work
- `ModelResponse` 新增 `usage: Usage | None = None`（带默认值 = 向后兼容
  的新增，不改签名）。`Usage` 归一化 input/output/cached tokens。
- OpenAI 后端解析 `prompt_tokens` / `completion_tokens` /
  `prompt_cache_hit_tokens`；Anthropic 后端解析 `input_tokens` /
  `output_tokens` / `cache_read_input_tokens`。厂商字段差异在各自 backend
  内消化。
- 新增 `UsageEvent`（model, input/output/cached tokens, latency_ms），
  `run_agent` 每次模型调用后产出。**不把 usage 挂到已有事件上**——事件
  语义不该被度量污染。
- 延迟在 `run_agent` 内计时（含网络与重试，即用户实际等待）。

## Seams (tdd, 先红后绿)
1. `OpenAICompatibleBackend.complete` → MockTransport 断言 usage 解析
   （含 cache 字段缺失时的降级）。
2. `run_agent` → FakeLLMBackend 携带 usage，断言 UsageEvent 产出次数与
   字段；无 usage 时不产出。

## Done when
- 上述 seam 测试绿；`make test` 全绿。
- 真机：一次 `ask` 能看到 UsageEvent 且 token 数非零。

## Resolution (closed 2026-08-19)

- `Usage`（input/output/cached tokens + model）加入 `llm/base.py`；
  `ModelResponse.usage` 为带默认值的新增字段，未改任何签名（§二 兼容）。
- 厂商差异在各自 backend 内消化：OpenAI 协议
  `prompt_tokens`/`completion_tokens`/`prompt_cache_hit_tokens`，
  Anthropic `input_tokens`/`output_tokens`/`cache_read_input_tokens`。
  服务端不返回 usage 时降级为 `None`，不抛错。
- **新增 `UsageEvent`** 而非把 usage 挂到已有事件上：度量不应改变语义
  事件的含义，且 runner/trace 可独立消费。延迟在 `run_agent` 内围绕整个
  调用计时（含后端重试）——度量的是用户真实等待。
- 5 个 seam 测试；`make test` 172 全绿。

**真机实测（重要发现）**：prompt 缓存命中率第一轮 256/1189 ≈ 22%，
第二轮起 1152/1407 ≈ 82%、1536/1894 ≈ 81%。系统提示（schema+口径）稳定
不变正是缓存杠杆所在，而 DeepSeek 缓存命中价差 30 倍 —— 这条进 T3 的
成本报告与 README。
