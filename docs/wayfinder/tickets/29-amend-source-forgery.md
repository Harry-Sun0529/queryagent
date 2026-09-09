---
status: closed
type: task
blocked_by: []
claimed_by: opus-session-2026-09-09
---
# T29 — amend 允许伪造「文档依据」来源

## Question

`QueryWorkflow.amend(..., rules)` 直接 `with_rules(rules)`，**对 `rule.source`
没有任何约束**；`Rule.__post_init__` 只检查 DOC 来源的 `evidence_ref` 非空，
任意字符串都放行。

今天 `cli.py` 硬编码 `RuleSource.USER` 所以打不穿，但那是**调用方自觉，不是
服务层保证**——而 `amend` 正是 Web/MCP 将来要调的 API。任何调用方都能构造
`Rule("counting_basis", "按首单日期", RuleSource.DOC, evidence_ref="随便编")`，
在确认单上得到一条带「文档依据」标签、引用却是伪造的规则。

这是 1A 留下的缺口。在 1B 让 DOC 规则第一次真的可被构造之前必须堵上，否则
「文档依据」这一档从落地第一天起就不可信。

## Work

- `amend()` 显式拒绝 `source is not RuleSource.USER`（用户补充的规则按定义
  就是本次约定）。
- `Rule.__post_init__` 的 docstring 写清楚"这只是非空断言，真正的引用有效性
  由 EvidenceDraftBuilder 保证"——否则未来一定有人以为类型系统已经保证了。

## Seams (tdd, 先红后绿)

1. `QueryWorkflow.amend` 拒绝非 USER 来源

## Done when

- K14：`amend` 传入 DOC 或 MAINTAINER 来源的规则被拒绝，且草案未被修改
  （版本不变、哈希不变）。
- 现有 345 passed / 1 skipped 不回退。

## Resolution（2026-09-09）

`amend()` 现在显式拒绝任何 `source is not RuleSource.USER` 的规则，并在拒绝时
保持草案原封不动（版本与哈希都不变）。379 passed / 1 skipped。

**为什么修在服务层而不是收紧 `Rule`**：`Rule` 是值对象，DOC 来源的规则本身是
合法的——1B 的抽取管线正要产出它们。不合法的是"**调用方在一次 amend 里自称
文档依据**"。约束属于那个动作，不属于那个类型。

顺带把 `Rule.__post_init__` 的 docstring 写清楚了：它只是非空断言，任意字符串
都能过；引用是否真的解析到该主体看过的片段由抽取管线在服务端确立。否则未来
一定有人以为类型系统已经保证了来源。
