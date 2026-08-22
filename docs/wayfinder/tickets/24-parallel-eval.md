---
status: open
type: task
blocked_by: [21]
claimed_by:
---
# T24 — eval 并行执行

## Question
200 题串行需 75 分钟，dev 100 题需 22 分钟。这直接决定改进迭代的节奏——
慢到让人不想迭代。而"并发瓶颈在哪"本身是 §七 的防御题。

## Work
- 按 case 并行（可配置并发度，默认保守值），每个 worker 独立的 connector
  与 backend；结果仍按 case id 排序输出。
- 增量落盘必须线程安全。
- 并发度过高会触发限流 → 与既有的重试/熔断协同。

## Seams (tdd)
1. 并行与串行在同一批 scripted 事件上给出相同的报告。
2. 增量日志在并发写入下不丢不串。

## Done when
- 两个 seam 测试绿；真机跑 dev 100 题，结果与串行一致、耗时显著下降。
