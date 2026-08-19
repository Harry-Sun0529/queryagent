---
status: closed
type: task
blocked_by: [01]
claimed_by: fable-session
---
# T2 — Trace 落盘与 replay

## Question
Agent 出错时目前无法复盘（事件流打完就消失）。如何落盘并回放，且默认
安全？

## Work
- `queryagent/trace.py`：TraceWriter / TraceReader，JSONL，每行
  `{"type": "<EventName>", ...fields}`；反序列化用类型注册表。
- CLI：**默认开**，写 `.queryagent/traces/<timestamp>-<slug>.jsonl`；
  首次写入时 stderr 打一条提醒（写到哪 / 含什么 / 怎么关）；
  `--no-trace` 与 config `trace: false` 两种关法。
- `queryagent replay <path>`：读回并用现有渲染器重放（`--verbose` 同效）。
- `.gitignore` 加 `.queryagent/`（比文档提醒更硬的隐私保护）。
- 保留上限：滚动保留最近 50 个 trace 文件。

## Seams (tdd)
1. 序列化 roundtrip：每种 AgentEvent 写出再读回后相等（含 ClarifyEvent
   的 tuple 字段、UsageEvent）。
2. TraceWriter 的保留上限行为。

## Done when
- roundtrip 测试覆盖全部事件类型；`make test` 绿。
- 真机：`ask` 后产生 trace 文件，`replay` 能还原出同样的轨迹。

## Resolution (closed 2026-08-19)

- `queryagent/trace.py`：JSONL 序列化（`type` tag + 类型注册表）、
  TraceWriter（懒创建文件、每行 flush——崩溃时正是最需要 trace 的时候）、
  `read_trace`、`new_trace_path`（时间戳前缀 → 天然可排序）、
  `prune_traces`（保留最近 50）。
- 反序列化按 dataclass field 逐个取值：payload 里没有的字段走默认值，
  因此**新增可选字段不会让旧 trace 读不出来**；JSON 无 tuple，声明为
  tuple 的字段（ClarifyEvent.conflicting_metrics）读回时还原。
- CLI：默认开，`--no-trace` 与 config `trace: false` 两种关法；
  `queryagent replay <path>` 始终全量渲染。
- 隐私提醒走 **stderr**（stdout 保持干净，`ask` 仍可管道传递），每进程
  一次；`.queryagent/` 进 .gitignore —— 比文档提醒更硬的兜底。
- 16 个 seam 测试；`make test` 188 全绿。

**真机验证**：ask 后产生 trace 文件、stderr 出现提醒、`replay` 完整还原
（含 USAGE 行）、`--no-trace` 不产生文件、`git check-ignore` 确认覆盖。
