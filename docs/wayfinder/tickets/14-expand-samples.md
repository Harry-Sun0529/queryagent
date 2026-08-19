---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T14 — 扩集：test 200 全新 / dev 100

## Question
现有 dev/test 各 30 题。配对比较需 57-114 题，30 题不够；且旧 test 的
逐条结果被观察过（看过哪些 case 编号失败），不再是纯净锚点。

## Work
- 从 BIRD mini-dev 500 题中**全新抽 200 题**作 test（seed 待定，写进
  ADR），与旧 30 题、与 dev 均不相交。
- dev 抽 100 题，**旧 30 道 test 题退役并入 dev 池**（它们已知的失败是
  现成的失因分析素材）。
- 两个 subset.json 进 repo；留 200 题备用（不可逆决定，必须留）。
- 所需数据库全部已在本地，零下载。

## Seams (tdd)
`sample_cases` 的多重排除（test 排除旧题、dev 排除 test）——不相交是
**被测试保证的性质**。

## Done when
- 不相交测试绿；两个 subset.json 落盘；打印各自需要的库并确认本地齐备。

## Resolution (closed 2026-08-19)

- 新 **test 200 题**（seed=2026，排除全部 60 道跑过/看过结果的旧题 ⇒
  逐条结果从未被观察过）；新 **dev 100 题**（60 道退役旧题 + seed=11 抽
  40 道）；**备用 198 题**（不可逆决定，坚持留）。11 个库本地齐备。
- 加了一个**数据层回归测试**（不相交 + 规模 + id 唯一），它立刻抓到一个
  真 bug：**上游 BIRD mini-dev 有 2 条完全重复的题**（financial_137/138
  各出现两次）。case id 是续跑日志与报告表的主键，重复会让 `--resume`
  把第二条当成已完成而静默跳过。
- 修法：完全相同的条目合并（重复计分等于给它双倍权重），仅 id 冲突但
  内容不同的加后缀保留两条——两种情况都不静默丢数据。题库 500 → 498。
