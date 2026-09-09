---
status: open
type: task
blocked_by: [30]
claimed_by:
---
# T31 — 语义检索与量化对照

## Question

关键词基线在同义业务表达上到底差多少？没有这个数字，"我做了 RAG"就只是
"我接了一个库"。

**需要第二把 key**：DeepSeek 官方文档没有 embeddings 端点（已核实），现有 key
只能对话。

## Work

- `knowledge/embedding.py`：`EmbeddingClient` 走 OpenAI 兼容 `/v1/embeddings`，
  照 `llm/openai_backend.py` 的手写 httpx 模式（构造函数收
  `client: httpx.Client | None`，测试用 `MockTransport` 零网络）。纯 Python
  余弦，**不引 numpy、不引向量库**。
- key 只从 `QUERYAGENT_EMBEDDING_API_KEY` 读。
- 索引加向量列；无 embedding 配置时降级为关键词并**明说降级了**（K10）。
- `eval/knowledge/` 合成电商语料与 gold 标注；合成文档只描述**规则**不写死
  数字（demo 数据的日期相对今天生成，写死会过期）。
- `eval/run_retrieval_check.py`：报告授权 gold 证据的 Recall@k（**分母只含该
  主体有权且适用的证据**）、引用定位正确率、无证据时的行为。

## Done when

- 关键词与语义**分别报告**，不合并成一个"RAG 准确率"。
- 同义问句集固定并提交（如「新增用户」/「拉新数」/「新注册多少人」）。
- 与 BIRD 封存 test200 完全无关，不侵入不读取。
- 启用云端 embedding 意味着文档内容离开本机——这一点在 README 与 SECURITY
  显著说明，不做成默认打开。
