---
status: closed
type: task
blocked_by: [30]
claimed_by: opus-session-2026-09-09
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

## Resolution（2026-09-09）

**代码完成，量化对照只跑出一半。** 诚实断点如下。

已交付：`EmbeddingClient`（OpenAI 兼容 `/v1/embeddings`，手写 httpx，测试用
`MockTransport` 零网络）、索引的向量列与 `embed_missing`（已有向量不重复付费）、
provider 的语义排序、固定同义问句集、`eval/run_retrieval_check.py`。
**不引向量库、不引 numpy**，余弦是纯 Python。

**关键词基线 Recall@3 = 9/13**，证据在
`eval/results/retrieval-2026-09-09-keyword-baseline/`。四条 miss 全部是与文档
**字面零重合的同义表达**（「内部测试的号」vs「测试账号」、「GMV」vs「成交额」、
「交易额归到哪一天」vs「归属到下单日期」、「同一个人买两次算几个人」vs
「去重用户数」）。

**语义那一行未测量**——DeepSeek 官方文档没有 embeddings 端点，需要第二把 key。
所以上面那四条 miss 是**引入语义检索的论据，不是语义检索有效的证据**，报告里
逐字这么写了。两者分别报告，不合并成一个"RAG 准确率"。

设计上一条值得记的：语义检索必须有**余弦下限**（0.35）。embedding 给任意两段
文本都有非零相似度，没有下限的话"没有相关证据"这个答案在语义模式下**永远不
可达**——不相关的问题也会拿回排第一的片段。这条有测试钉着。

另一条：语料未 embed 时**回退关键词而不是返回空**。未 embed 是"安装步骤没跑"，
返回空会把它说成"文档没有相关内容"——又是同一类不该混的断言。

后续要补的一步：拿到 embedding key 后跑
`python eval/run_retrieval_check.py --output eval/results/retrieval-<日期>`，
补齐对照行。
