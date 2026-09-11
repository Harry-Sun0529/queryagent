---
status: open
type: task
blocked_by: [48]
claimed_by:
---
# T47 — 在 1.0 代码上重跑基准

## Question

自建集补跑一直没做（交接文档记着 selfbuilt36 是稍早代码的结果）；README 的数字停在旧版本。
1.0 要发布的数字必须来自 1.0 的代码。

## Work

- 自建 36 条跑 3 次报区间；BIRD dev100 跑 1 次（dev 部分可在 T48 之前跑）。
- 封存 test200 在接口冻结后跑一次，作为 1.0 的数字；之后不因它改任何东西（ADR-004）。
- 只有 DeepSeek 一组数（强模型无 key），照实写；输出到新目录，不覆盖旧结果。

## Done when

- README 与 `eval/results/` 的数字标明日期与代码版本；运行签名与 manifest 完整。
