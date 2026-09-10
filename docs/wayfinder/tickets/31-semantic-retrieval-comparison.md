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

## 补记（2026-09-10）：对照补齐，并推翻了上面一条设计结论

拿到硅基流动的 key 后补跑，证据在
`eval/results/retrieval-2026-09-10-floor-0.50/`：

| 方案 | Recall@3 | 不相关问题误检 |
|---|---:|---:|
| 关键词 | 9/13 | 0/8 |
| 语义（bge-m3，下限 0.5） | 12/13 | 1/8 |

同义问句集在测量前已冻结（9 月 9 日随 `5ee4784` 入库，其间未改）。

**上文"余弦下限 0.35，这条有测试钉着"是错的。** 测试钉住的是假向量上的行为；
真模型上 0.35 让 8 条不相关问题中的 6 条拿回"证据"。正确证据最低 0.535、不相关
最高 0.549，两个分布重叠，不存在能分干净的单一阈值。处理：

- 下限改为 `LocalKnowledgeProvider(min_similarity=...)` 与配置项
  `knowledge.embedding.min_similarity`，默认 0.5；拒绝 `(0, 1)` 以外的值。
- 默认值是看过不相关问题集的分数后选的，**误检 1/8 是样本内数字**，报告与 README
  都这么写。
- 评测补上此前 Done-when 写了、脚本却漏掉的"无证据时的行为"——另起
  `eval/knowledge/unrelated.yaml`，不动已冻结的同义问句集。

**另一处文档与实现不符**：README/CHANGELOG 说语义检索"配置即可开启"，但配置加载器
从未读取 `embedding` 段、`flow` 永远构造不带 embedder 的 provider——语义检索只在
评测脚本里可达。现已接上：`kb import` 生成向量并说明正文发往了哪个端点；`flow` 在
语义已配置但该业务空间尚无向量时，明说本次按关键词检索（K10）。

教训：**阈值类参数只在假数据上测过，等于没测。**
