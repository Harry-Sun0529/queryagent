---
status: open
type: task
blocked_by: [27]
claimed_by:
---
# T28 — 本地索引与授权检索（关键词基线）

## Question

权限必须在检索前生效，而不是检索后遮盖。怎样的接口形状能让"检索后再过滤"
**根本写不出来**？

## Work

- `KnowledgeProvider` Protocol 的每个方法都收 `RetrievalScope`，**不提供
  不带 scope 的重载**；`RetrievalScope` 只能由 `ActorContext` 经唯一构造点
  派生。没有"返回全量再过滤"的形态可写。
- `knowledge/index.py`：`SqliteKnowledgeIndex`，形状照 `workflow/store.py`
  （`isolation_level=None`、WAL、编解码函数成对）。**workspace 过滤写进
  SQL 的 WHERE 子句**。
- `knowledge/keyword.py`：关键词基线。复用 `metrics/yaml_store.py` 里调过参
  的 `_tokens()`（ASCII 词 + CJK bigram），提取到 `text.py` 共用。
- `knowledge/provider.py`：`LocalKnowledgeProvider` 实现 search/read/check_refs。
- **provider 一致性测试套件**：参数化，任何实现都要跑通。这是唯一能防止未来
  第二个 provider 悄悄破功的机制。
- `queryagent kb import` / `kb list` CLI；配置段 `knowledge:`。
- 路径约束：`sources[].path` 必须落在配置声明的目录内，`Path.resolve()` 归一化
  + 前缀校验，拒绝符号链接逃逸——否则会把 `.env`、`deepseek.env` 当文档读进
  prompt。
- 凭据键拒绝逻辑目前只在 `_load_llm` 内（`config.py:131`），**必须提成共用
  函数并应用到 `knowledge.embedding`**。

## Seams (tdd, 先红后绿)

1. `SqliteKnowledgeIndex.upsert / search(scope, ...)`
2. `LocalKnowledgeProvider.search / read / check_refs`
3. `scope_of(actor) -> RetrievalScope`

## Done when

- K3：跨 workspace 的正文与标题不出现在任何返回对象里。
- 撤权与内容变更能被 `check_refs` 区分为 UNAVAILABLE / CHANGED，且对外不区分
  撤权与删除。
- `kb import` 打印实际纳入的文件清单；路径逃逸被拒绝且有测试。
- `tests/test_metrics.py` 在分词器提取后行为不变。
