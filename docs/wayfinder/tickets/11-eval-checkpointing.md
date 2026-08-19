---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T11 — eval 断点续跑

## Question
eval 报告只在**全部跑完**后才写盘。扩集后单轮 45 分钟，中途失败（网络、
限流、Ctrl-C）会丢掉全部已付费的结果——与上一轮修掉的「一个坏库毁全局」
是同一类缺陷，只是触发原因不同。

## Work
- 每个 case 完成后把结果**增量落盘**（JSONL），崩溃后可从中断处续跑。
- `--resume` 读回已完成的 case，跳过它们，只跑剩下的。
- 中断（KeyboardInterrupt）时也要保住已完成部分并提示如何续跑。

## Seams (tdd)
1. 增量文件的写入/读回 roundtrip（含部分完成）。
2. `main(["eval", ..., "--resume"])`：已完成的 case 不重跑，报告含全部结果。

## Done when
- seam 测试绿；模拟中途中断后 `--resume` 能补齐并产出完整报告。

## Resolution (closed 2026-08-19)

- `queryagent/evals/checkpoint.py`：`ResultLog` 每完成一个 case 立刻
  append 到 `<output>.partial.jsonl` 并 flush（能幸存于 abrupt end 才是
  重点）；`--resume` 读回已完成的 case 并跳过。
- **不带 `--resume` 时会删除旧日志**：一次全新运行不该悄悄继承另一次
  （可能配置不同的）运行的结果。
- 反序列化与 trace 同样按 field 逐个取值 + 还原 tuple 字段，残缺尾行跳过。
- 2 个 seam 测试（增量落盘、续跑不重付）。
