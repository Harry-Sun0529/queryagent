---
status: open
type: task
blocked_by: [28, 29]
claimed_by:
---
# T30 — 证据驱动的草案与引用验证

## Question

产品价值在这一张票落地：确认单上第一次出现带出处的「文档依据」。

核心难题不是"怎么让模型抽取规则"，而是**怎么让模型抽不出坏引用**。详见
[技术方案 §4.5](../../specs/workflow-slice-1b-2026-09.md)。

## Work

- **模型不返回引用字符串，只返回本次检索结果的下标**。服务端用下标取对象、
  自己生成 `evidence_ref`。编造引用、引用未检索到的片段、引用无权片段——三件
  事一次性变成无法表达的状态。
- `workflow/extraction.py`：S0–S4 验证管线。**S1 解析失败整份失败，S2 逐条
  丢弃**——必须区分「文档没说」和「我们没读成功」，前者是关于世界的陈述，
  解析 bug 不能被渲染成它。
- 支持性检查：L1 逐字引文（偏移由服务端 `find` 算，**不要求模型返回偏移**）
  + 数字落地检查（value 里每个数字都必须在 quote 中）+ trigram 粗筛。
- `workflow/evidence_builder.py`：冲突 → 带引用的候选；必需键没填上 → missing。
  **必需键由维护者在 metrics.yaml 声明，抽取结果只能填洞不能造洞**。
- `check_refs` 接进 `confirm()` 与 `execute()`；执行顺序为 身份 → 确认匹配 →
  status → check_refs → compile → claim 幂等键，保持 1A "拒绝时数据库未被
  触碰、不烧幂等键"的性质。
- `store.expire_draft()`：**只改 status，不递增 version、不改哈希**，否则
  version 校验会先失败，把"依据失效"掩盖成"口径改版了"。
- `evidence_ref` 里进哈希的只有稳定部分（doc_id + chunk_id + span），
  **`doc_version` 不进哈希**——否则改个错别字就让所有历史确认失效，造成确认
  疲劳，用户开始盲点确认，安全性净下降。
- `render.py` 扩展：DOC 规则显示 文件 · 章节 · 位置，并展示引文原文。
- 未配 `knowledge:` 时退回 1A 的 `MetricDraftBuilder`，不新开旁路。

## Seams (tdd, 先红后绿)

1. `validate_extraction(chunks, raw) -> (rules, diagnostics)`
2. `EvidenceDraftBuilder.build(actor, question) -> BusinessDefinition`
3. `QueryWorkflow.confirm/execute` 的 check_refs 接入
4. `SqliteWorkflowStore.expire_draft`

## Done when

- K1/K2/K13/K15：下标越界、引文不逐字、模型多塞字段、数字对不上，四条都被丢弃。
- K4/K11/K12：注入语料不产生确认记录、不改状态机、业务 SQL 计数为 0；文档正文
  只出现在证据区且被定界符包裹；抽取调用不带工具。
- K5/K16：撤权与文档变更 → EXPIRED；片段哈希变化不改 `definition_hash`。
- K6/K7：冲突并列可选、缺失显式。
- K9：未配 `knowledge:` 时行为与 1A 逐字节一致。
- ADR-007 写成（收窄 ADR-002 而非违反）；README/SECURITY/CONTEXT 同步整改。
