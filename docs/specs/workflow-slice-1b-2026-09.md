# 切片 1B：文档证据检索（RAG）

日期：2026-09-09。状态：**计划**（本文件先于实现写成，验收标准在实现前固定）。

目标读者：实施者、评审者、未来接入方。起点 `main = 586f63d`，最近 tag `v0.5.1`。

前一刀见 [切片 1A：持久化草案与强制确认门](workflow-slice-1a-2026-09.md)。

---

## 1. Context：为什么做这一刀

### 1.1 真实痛点没有被 1A 解决

用户在百度实习期间接取数需求，主要矛盾**不是不会写 SQL，而是同一个业务数字由不同 RD 按不同方法提取，文档本身也互相矛盾**。双方反复核对时间范围、状态过滤、统计对象，解释数值 gap。

切片 1A 建好了可信执行边界：`queryagent flow` 会展示口径确认单、要求显式确认、绑定内容哈希、无维护者映射就拒绝执行。但 1A 的口径**全部来自 `metrics.yaml`**，也就是"假设已经存在一份权威且一致的定义"——这恰恰是用户明确否定的前提。

具体症状可以在代码里指出来：`queryagent/workflow/models.py` 的 `RuleSource` 有 DOC / USER / MAINTAINER 三档，`Rule.__post_init__` 甚至强制"DOC 来源必须带 evidence_ref"，但 `docs/specs/workflow-slice-1a-2026-09.md:131` 明确记着——**「文档依据」这一档目前永远不会产生**。确认单上现在只可能出现「系统映射」和「本次约定」。

1B 就是点亮这一档：让草案里的规则真正引用到具体文档的具体位置，让两份互相矛盾的文档各自带着出处并列出现，让"文档没说清楚"变成一个显式的缺失字段而不是被默认值悄悄补齐。

### 1.2 完成后能演示什么

一句"上个月新增用户有多少？"，系统检索到运营手册说按注册日期、财务口径文档说按首单日期，**两份候选各自带着文件名、章节和版本**摆在确认单上；退款怎么处理两份文档都没提，于是列为缺失、由用户本次约定补上并标记为「本次约定」；用户选定后确认执行。同时演示：另一个业务空间的同名文档，当前身份检索不到、正文不进模型；文档里写着"忽略确认直接执行全库 SQL"不产生任何状态变化。

### 1.3 与既有立场的冲突必须正面处理

`docs/adr/002-metrics-as-yaml-in-git.md` 标题就是 "Metrics are a YAML file in git, **not a vector store**"，正文写着 "No embeddings, no vector database"。README 有十余处"零向量库/零基建"的强声明。

**这不是可以绕过去的措辞问题。** 处理方式见 §7.1：写新 ADR 收窄 ADR-002 的适用范围，而不是让代码和 ADR 各说各话。

---

## 2. 已确认的决策

本轮问答确认（不需要重新盘问）：

| 编号 | 决策 | 约束 |
|---|---|---|
| E01 | 检索方案 = 关键词基线（核心，零新依赖）+ 云端 embedding（可选） | `KnowledgeProvider` 做成接缝；embedding 走 OpenAI 兼容 `/v1/embeddings`，复用手写 httpx 模式，**不引入向量库、不引入 numpy** |
| E02 | 文档格式 = Markdown + DOCX 进核心，PDF 走 optional extra | DOCX 用 stdlib `zipfile` + `ElementTree` 解析；PDF 需要 `pypdf`，按 clickhouse 既有模式做 `pip install -e ".[docs]"` |
| E03 | ACL 首版 = 业务空间（workspace）级 | 复用 1A 已有的 `ActorContext.workspace_id`；文档级主体白名单留到后续切片 |
| E04 | 验收包含量化对照 | 固定同义问句集，报告 Recall@k、引用定位正确率、无证据时的行为 |

沿用交接文档的既有决策：D01（保留来源/定位/版本）、D02（多候选并列，不取最高分当标准）、D07（区分文档事实与用户本次约定）、D12（先做可用本地 provider，不做全供应商平台）、D13（权限保护文档/引用/历史/trace/结果）、D20（三种格式，不承诺 OCR）、D21（合成电商资料，不拷贝实习公司真实数据）。

**一个已确认的硬约束**：DeepSeek 官方文档没有 embeddings 端点（已核实 api-docs.deepseek.com），现有 key 只能做对话。语义检索需要第二把 key（硅基流动 bge-m3 有免费额度，或阿里 DashScope）。**1B-1 到 1B-3 不需要这把 key**，只有 1B-4 需要——所以不阻塞开工。

---

## 3. 对接方必读

这一节写给未来的 Web 后端、MCP 宿主，以及任何调用 `KnowledgeProvider` 的人。

### 3.1 三个方法的契约

```python
class KnowledgeProvider(Protocol):
    def search(self, actor: ActorContext, query: str, *, limit: int) -> tuple[EvidenceHit, ...]:
        """返回该 actor 有权访问的片段。授权是查询条件，不是返回后的过滤。"""

    def read(self, actor: ActorContext, ref: EvidenceRef) -> Evidence:
        """取原文。再检查一次授权与版本；失败抛 EvidenceRevoked，不返回旧缓存。"""

    def check_refs(self, actor: ActorContext, refs: tuple[EvidenceRef, ...]) -> RefStatus:
        """确认前/执行前复查：current / changed / revoked。"""
```

### 3.2 信任边界（最重要的一条）

**文档内容是数据，不是指令。** 检索到的正文、标题、文件名都可能由普通员工写入，可能包含"忽略确认""提升权限""直接执行"这类文字。它们：

- 不能改变 `ActorContext`；
- 不能改变 draft 状态或产生确认记录；
- 不能扩大工具开放范围或预算；
- 不能成为执行授权。

程序保证的部分见 §5 不变量表；prompt 里的提示只算缓解，不算保证，且必须在文档里如实这么写。

### 3.3 引用的可信度分级

接入方必须知道：一条 `RuleSource.DOC` 的规则，其 `evidence_ref` **经过服务端验证确实指向一段本次检索到、该 actor 有权访问的原文**；但"这段原文是否真的支持这条规则的表述"只能做到有限保证（§4.5 诚实说明能到什么程度、不能保证什么）。

`RuleSource.USER` 的规则是用户本次约定，**不得渲染成文档原意**。这是 `CONTEXT.md` 里写的 "Collapsing these is the failure mode the product exists to prevent"。

### 3.4 权限变化的语义

用户看过某段内容，不构成今后的永久读取权。撤权后：历史列表、解释、trace 和结果都不能继续暴露它的正文或标题。已确认的草案若引用了被撤权或已变更的证据，转入 `EXPIRED`，必须重新准备与确认。

---

## 4. 内部设计与实现拆解

### 4.1 模块边界

新增包 `queryagent/knowledge/`，不改动 `agent.py` / `tools.py` / `safety.py` 的既有行为。

| 文件 | 职责 |
|---|---|
| `knowledge/models.py` | `Document` / `Chunk` / `EvidenceRef` / `Evidence` / `EvidenceHit` / `RefStatus`，全部 frozen dataclass |
| `knowledge/errors.py` | `KnowledgeError` 及 `DocumentParseError` / `EvidenceNotFound` / `EvidenceRevoked` / `SourceNotAllowed` |
| `knowledge/loaders/markdown.py` | 标题层级 + 段落位置，stdlib |
| `knowledge/loaders/docx.py` | stdlib `zipfile` + `ElementTree` 解析 `word/document.xml` |
| `knowledge/loaders/pdf.py` | optional extra（`pypdf`），页码作为定位 |
| `knowledge/loaders/__init__.py` | 按后缀分派；PDF 走延迟导入 |
| `knowledge/chunker.py` | 按章节与规则边界切片，保留相邻说明与定位信息 |
| `knowledge/index.py` | `SqliteKnowledgeIndex`：导入、更新、**带 workspace 过滤的检索** |
| `knowledge/keyword.py` | 关键词检索基线 |
| `knowledge/embedding.py` | `EmbeddingClient`（httpx）+ 纯 Python 余弦 |
| `knowledge/provider.py` | `LocalKnowledgeProvider` 实现三方法契约 |
| `workflow/evidence_builder.py` | `EvidenceDraftBuilder`：证据 → 候选规则 / 冲突 / 缺失 |
| `workflow/extraction.py` | LLM 抽取结果的**服务端验证管线**（§4.5） |
| `text.py`（新，见下） | 共享分词 |

### 4.2 值得复用的既有代码

- **分词器**：`queryagent/metrics/yaml_store.py` 的私有 `_tokens()` 已经实现了"ASCII 词 + CJK bigram"的零依赖分词，并且是调过参的（`_MIN_SCORE = 2.0` 那段注释记录了为什么单个 bigram 是噪声）。建议提取到 `queryagent/text.py::tokens()`，`yaml_store` 与 `knowledge/keyword.py` 共用。这是小而诚实的重构，不改匹配行为，`tests/test_metrics.py` 必须保持全绿。
- **可选依赖模式**：`queryagent/connectors/clickhouse.py`（顶部裸 import + docstring 声明契约）、`connectors/__init__.py:23-34`（工厂内延迟导入）、`cli.py:_explain`（ImportError → 可操作的中文提示 + 退出码 2）、`tests/test_cli_errors.py:78-99`（`monkeypatch.setitem(sys.modules, ...)` 验证提示）。PDF extra 完整照抄这六个位置。
- **httpx 手写客户端**：`queryagent/llm/openai_backend.py` 的构造函数带 `client: httpx.Client | None = None`，测试用 `httpx.MockTransport` 零网络验证。`EmbeddingClient` 照此写，测试同样零网络。
- **持久化**：`queryagent/serde.py::rebuild_dataclass` 处理"缺字段回落默认值 + list 还原 tuple"，任何落盘的 frozen dataclass 都该走它。嵌套 dataclass 参照 `evals/checkpoint.py:29-34` 的手工组装模式。
- **SQLite 存储骨架**：`queryagent/workflow/store.py` 的形状（`isolation_level=None`、WAL、按 subject 归属检查、编解码函数成对）直接照搬给 `SqliteKnowledgeIndex`。
- **1A 的确认单渲染**：`workflow/render.py` 的 `_SOURCE_LABELS` 已经有「文档依据」这一档的中文文案，1B 只是让它第一次真的被用到。

### 4.3 四个子切片（小步快跑，每步独立可提交、独立绿）

**1B-1 文档导入与切片**（无检索、无持久化）
- 交付：`knowledge/models.py`、`errors.py`、`loaders/*`、`chunker.py`
- 纯函数：`load_document(path) -> Document`、`chunk_document(doc) -> tuple[Chunk, ...]`
- 每个 chunk 携带：来源文件、章节标题路径、位置（行号/段落序号/页码）、内容哈希
- 解析失败必须显式告知"此资料未成功纳入"，不能返回空文本假装没有相关规则
- 测试：`tests/test_knowledge_loaders.py`、`tests/test_knowledge_chunker.py`，fixture 用 `tmp_path` 现写 md/docx

**1B-2 本地索引与授权检索（关键词基线）**
- 交付：`index.py`、`keyword.py`、`provider.py`、`text.py` 提取、`queryagent kb import` / `kb list` CLI、配置段 `knowledge:`
- **workspace 过滤写进 SQL 的 WHERE 子句**，不是取回后再过滤
- 测试：`tests/test_knowledge_index.py`、`tests/test_knowledge_provider.py`

**1B-3 证据驱动的草案**（产品价值在这里落地）
- 交付：`workflow/extraction.py`、`workflow/evidence_builder.py`，接进 `flow`
- 配了 `knowledge:` 就用 `EvidenceDraftBuilder`，没配则退回 1A 的 `MetricDraftBuilder`（不是新开一条绕过确认门的路径）
- 确认单上第一次出现「文档依据」；冲突 → 带引用的候选；文档没说清楚 → 缺失字段
- `check_refs` 在 confirm 与 execute 前调用，撤权/变更 → `DraftStatus.EXPIRED`（**该状态在 1A 定义了但至今无人产生，1B 给它第一个生产者**）
- 测试：`tests/test_evidence_extraction.py`、`tests/test_evidence_builder.py`、扩充 `tests/test_cli_flow.py`

**1B-4 语义检索与量化对照**（需要第二把 key）
- 交付：`embedding.py`、索引里的向量列、`eval/knowledge/` 合成语料与 gold 标注、`eval/run_retrieval_check.py`
- 报告：授权 gold 证据 Recall@k（分母只含该主体有权且适用的证据）、引用定位正确率、无证据时的行为
- 无 embedding 配置时降级为关键词并**明说降级了**，不静默

### 4.4 配置形态

```yaml
knowledge:
  index_path: .queryagent/knowledge.db
  sources:
    - path: examples/knowledge/ops
      workspace: ops
    - path: examples/knowledge/finance
      workspace: finance
  embedding:                     # 可选；缺省则只用关键词基线
    base_url: https://api.siliconflow.cn/v1
    model: BAAI/bge-m3
    # key 只从 QUERYAGENT_EMBEDDING_API_KEY 读，绝不进配置文件
```

`sources[].path` 必须落在配置文件声明的目录内，导入时做真实路径归一化与前缀校验，拒绝符号链接逃逸——否则文档扫描器可能把 `.env`、`~/.config/queryagent/deepseek.env` 当文档读进 prompt（§6.2）。

### 4.5 引用验证管线（本切片最难的一段）

模型会做四件坏事：编造不存在的引用；引用真实存在但本次没检索到、或该身份无权访问的片段；引用真实且授权的片段但内容与规则无关（伪引用）；把文档里的注入文字当成「文档依据」写进规则。

**关键认识：这四件事不该当成同一个校验问题解。** 前三件可以从数据流上消灭，让模型根本无法表达一个坏引用；第四件在原理上无法确定性证明，只能粗筛加人审。把两半混成一条"校验管线"是这个设计最容易翻车的地方。

#### 4.5.1 让坏引用无法被表达

**模型不返回 `evidence_ref` 字符串，它返回本次检索结果列表的下标。**

```python
# LLM 的输出 schema 只有这四个字段
{"rules": [{"key": ..., "value": ..., "citation": <int>, "quote": "<原文逐字片段>"}]}
```

服务端用下标取对象、自己生成 `evidence_ref`。这一步一次性消灭三件事：编造引用（模型给不出引用字符串）、引用未检索到的片段（下标只能落在本次列表内）、引用无权片段（列表本身就是权限过滤后的产物）。剩下要校验的只有下标越界、引文不逐字、语义不支持、value 被污染——一个小得多的问题。

权限则做进接口形状：`KnowledgeProvider` 的每个方法都必须收 `RetrievalScope`，**Protocol 里不存在不带 scope 的重载**，`RetrievalScope` 只能由 `ActorContext` 经唯一构造点派生。这样"检索后再遮盖"在这个接口下**写不出来**——没有一个返回全量再过滤的形态。

再配一套 **provider 一致性测试套件**（参数化，任何实现都要跑通），至少包含"跨 workspace 的正文不出现在检索结果的任何字段中"。这是唯一能防止未来第二个 provider（企业知识库 connector）悄悄破功的机制。

#### 4.5.2 管线各阶段与降级方向

| 阶段 | 检查 | 失败时 |
|---|---|---|
| S0 检索 | provider 抛权限/不可用错误 | **整份失败**，不产出空草案 |
| S1 解析 | 模型输出是合法 JSON 且顶层结构符合白名单 | **整份失败** |
| S2.1 | `key` ∈ 维护者声明的允许键集合 | 丢弃该条 |
| S2.2 | `citation` ∈ `[0, len(chunks))` | 丢弃该条 |
| S2.3 | `chunks[citation].workspace_id == actor.workspace_id` | 丢弃该条 **并记为 anomaly**（这条本该不可能，触发即说明上游坏了） |
| S2.4 | 归一化后 `quote` 是该片段正文的子串；**偏移由服务端 `find` 计算** | 丢弃该条 |
| S2.5 | `quote` 长度在 `[8, 500]` 字符内 | 丢弃该条 |
| S2.6 | 支持性粗筛（§4.5.3） | 丢弃该条 |
| S2.7 | value 卫生：长度上限、单行化、控制字符剥离、命令式模式黑名单 | **丢弃，不清洗后保留** |
| S3 冲突 | 同一 key 有多条幸存且取值不同 | 全部转为候选（各带自己的引用），该键进 `missing` |
| S4 补洞 | 维护者声明的必需键没有幸存规则 | 该键进 `missing` |

**为什么 S1 整份失败而 S2 逐条丢弃——这是本节唯一真正重要的语义决定。** 逐条丢弃后该键进 `missing`，确认单上显示"文档没说清楚"，那是一个**关于世界的陈述**。解析 bug 绝不能被渲染成这个陈述。必须区分「文档没说」和「我们没读成功」。

**降级方向永远是「文档依据」→「本次约定」，绝不反向。** 一条被丢弃的 DOC 规则最终变成"必须由用户显式补充并标记为本次约定"——`missing` 进内容哈希，而 1A 的 `confirm()` 已经拒绝不完整草案。

**S2.7 为什么丢弃而不清洗**：清洗后的 value 是一个没有任何人（模型、原文、用户）审过的新字符串，把它挂上「文档依据」标签比丢掉更糟。

所有丢弃都产出结构化 diagnostic `(key, reason, citation)`，进 trace，不进确认单。没有 diagnostic，阈值无从调整。

#### 4.5.3 "引用真的支持规则"能做到什么程度

诚实分级：

- **L0 存在性/授权性——可确定性证明**，且是由 §4.5.1 的构造保证的，不是校验出来的。
- **L1 引文真实性（逐字出自该片段）——可确定性证明**。实现上有一条关键选择：**不要求模型返回字符偏移，只要求它返回 quote 文本，偏移由服务端 `find` 算**。模型算字符偏移几乎必错，中文尤甚（token 边界与字符边界完全不对齐）。要求它算偏移，等于把一个可解问题（子串匹配）换成一个不可解问题（模型算术），换来的漏杀全是真规则。
- **L2 语义支持——不可确定性证明。**

L2 三条路的代价：逐字子串（`value ⊂ quote`）漏杀灾难性，因为正常抽取必然改写，产品会退化成"一切都是 missing"；纯 n-gram 覆盖率在短文本上假阳性高，**而且数字和单位在 n-gram 里权重极低，偏偏"7 天写成 30 天"是最贵的错误**；要求模型返回 span 偏移在中文场景基本不可用。

**推荐方案 = L1 + 两条便宜的确定性检查：**

1. **数字/单位落地检查（主力）**：从 value 中抽出所有数字 token，每一个都必须出现在 quote 中，否则丢弃。直击最贵的一类错误，完全确定性、易测。中文数字做一个小规范化表（七/7、十五/15），只做常见几个，规范化失败按"未通过"处理（保守方向）。
2. **字符 trigram 覆盖率 ≥ θ（默认 0.35，可配置）**：定位是**完全不相关的粗筛**，只用来丢弃，不用来给"更可信"打分。文档里就写它是 smoke filter。

**中文特有的坑（单独测）**：归一化必须做 NFKC、全角/半角标点统一、空白折叠（DOCX/PDF 提取会插软换行，不折叠永远匹配不上）、去零宽字符。**归一化只用于比较，不能用于展示**；但若在归一化文本上算偏移再回原文切片就会错位。最小可行做法是**在归一化文本上存 span，并把归一化后的 quote 原样快照下来**，展示时直接用快照，不回原文重切——绕开写字符映射表这种高错误率代码。代价是展示的引文标点可能与原文有细微差异，可接受且必须写进文档。

**明确不能保证**（这段逐字进"不承诺"）：不保证 value 是 quote 的正确概括；不检测**断章取义**（引了适用条件的从句、丢了主句限定——这是最真实的失败模式，而且看起来完全合规）；不检测**跨段合成**（真规则常横跨两段，我们只允许单段引用，模型被迫选一段，可能选到较弱那段）；不保证文档本身是对的（可能引用了一段已废弃但仍在库里的口径）。

因此确认单**必须直接展示 quote 原文与文档名**。支持性检查的产品定位是"降低人审成本"，不是"替代人审"。

#### 4.5.4 引用不能进内容哈希的稳定部分之外

`models.py` 的 `content_hash()` **已经把 `evidence_ref` 算进去了**。如果把 `doc_version` 塞进引用字符串，那么文档改一个错别字 → 片段哈希变 → 定义哈希变 → 所有历史确认失效。在文档频繁小改的真实环境里这会造成确认疲劳，用户开始盲点确认，**安全性净下降**。

所以：**引用里进哈希的只有稳定部分（`doc_id` + `chunk_id` + quote span），`doc_version` 不进哈希**，文档变更走 `check_refs` → `EXPIRED` 这条独立通道。内容哈希回答的是"用户确认的语义被改了吗"，`check_refs` 回答的是"依据还成立吗"。两个问题混进一个字段，两个都答不好。

#### 4.5.5 必需键必须由维护者声明

`confirm()` 拒绝不完整草案。如果"必需键集合"由抽取结果反推，那模型多抽一个键、又被校验丢掉，就凭空产生一个阻塞项，草案将几乎永远不完整、1B 在真实文档上不可用。**必需键必须由维护者在 `metrics.yaml` 里显式声明，抽取结果只能填这些洞，不能创造新洞。**

#### 4.5.6 撤权与变更如何触发 EXPIRED

```python
class RefStatus(Enum):
    OK = "ok"
    CHANGED = "changed"           # 片段内容哈希不一致
    UNAVAILABLE = "unavailable"   # 撤权或删除，对外不区分
```

内部可区分"撤权"与"删除"用于运维日志，**对外一律归一成"不可用"**——区分它们本身就是存在性泄露，与 1A 的 `PermissionDenied` 是同一个问题。

判定用**片段内容哈希**而不是 mtime 或版本号：mtime 会因格式化、同步工具 touch 而误报；版本号在本地文件 provider 上根本不存在。文档级哈希可做快速路径，但判定以片段哈希为准。

调用时机：

1. **`confirm()` 内、产生确认记录之前**——用户点确认时，单子上的引用必须仍然有效。
2. **`execute()` 内**，顺序为：身份 → 确认匹配 → status → **check_refs** → compile → claim 幂等键。这是"确认到执行之间发生撤权也不会执行"的唯一保证点，也保持了 1A "拒绝时数据库未被触碰、不烧幂等键"的既有性质。
3. **渲染确认单之前**——尽力而为的 UX，不是安全边界；失败时标 EXPIRED 并渲染"依据已失效"，不把读操作变成异常。
4. 后台扫描可以有，但不能是唯一保证；定时任务必然有窗口，正确性来自 1、2 两处同步检查。

**EXPIRED 只改 status，不递增 version、不改哈希。** EXPIRED 不是语义变更；递增 version 会让 `execute()` 里的 version 校验先失败，把真实原因（依据失效）掩盖成"口径改版了"。这需要给 store 加一个最小方法 `expire_draft(subject_id, draft_id, *, expected_version)`，只更新 status——这是对 1A store 的唯一必要扩展。

**不拆出 REVOKED 状态**：对外不可区分的两件事，不该在对外可见的状态枚举里分开。对外统一措辞"依据已失效，需要重新生成确认单"，真实原因只进 trace。

"用户已经看过的内容"分三层，别混：(a) 已送达用户的输出收不回来，别假装能；(b) 渲染路径撤权后遮盖，只显示"该引用已不可用"；(c) quote 快照**保留但打标记，只允许审计路径读**——删掉就再也无法回答"当时我们给用户看了什么"，而这是本产品最重要的审计问题。但保存文档摘录是必须向部署方明示的隐私事实，给配置项 `knowledge.snapshot_quotes`，false 时只存哈希。**这个取舍由部署方做，不替他们做。**

#### 4.5.7 顺带修 1A 留下的一个真实缺口

`service.py` 的 `amend(..., rules)` 直接 `with_rules(rules)`，**对 `rule.source` 没有任何约束**；`Rule.__post_init__` 只检查 DOC 规则的 `evidence_ref` 非空，任意字符串都放行。今天 `cli.py` 硬编码 `RuleSource.USER` 所以打不穿，但那是调用方自觉，不是服务层保证——而 `amend` 正是 Web/MCP 将来要调的 API。任何调用方都能凭空造出一条带「文档依据」标签、引用却是伪造的规则。

修法：**`amend()` 显式拒绝 `source is not RuleSource.USER`**，并配不变量测试；同时把 `Rule.__post_init__` 的 docstring 写清楚"这只是非空断言，真正的引用有效性由 EvidenceDraftBuilder 保证"——否则未来一定有人以为类型系统已经保证了。

### 4.6 确认单要多显示什么

`workflow/render.py` 已经有「文档依据」文案（`_SOURCE_LABELS`），1B 让它第一次真的被用到。但当前 `render_draft` 只打印规则值，不打印出处。需要扩展：DOC 来源的规则要显示 `文件 · 章节 · 位置 · 版本`，以及被引用的原文片段。这是 D01「不能只有无出处总结」的落点。

---

## 5. 不变量与验收矩阵

沿用 1A 的编号风格（`I` = 本切片不变量，`T` = 交接文档 §17.2 用例号）。每条负面断言都必须成对：抛出正确的拒绝 **且** 副作用为零。

| 编号 | 不变量 | 对应 |
|---|---|---|
| K1 | 模型给出菜单外的 `evidence_id` → 该规则被丢弃，不出现在草案里 | 伪引用 |
| K2 | 模型给出的 `quote` 不在被引片段正文中 → 该规则被丢弃 | 伪引用 |
| K3 | 跨 workspace 文档的正文与标题，不出现在 `search`/`read` 的任何返回对象里，**也不出现在送给模型的 prompt 文本里** | T06 |
| K4 | 含注入文字的文档：不产生确认记录、不改变状态机、业务 SQL 执行计数为 0 | T08 |
| K5 | 检索后撤权或文档变更 → `confirm` 与 `execute` 均失败，草案转 `EXPIRED`，旧缓存不能绕过 | T07、T11 |
| K6 | 两份文档对同一 `rule_key` 给出不同取值 → 两个带出处的候选并列，选定前不能确认 | T03、D02 |
| K7 | 文档完全没提到某关键规则 → 该键出现在 `missing`；用户补充后标「本次约定」，不伪造 doc 来源 | T04、D07 |
| K8 | 文档解析失败 → 明确告知"此资料未成功纳入"，不返回空文本假装没有相关规则 | T25、D20 |
| K9 | 未配置 `knowledge:` 时，`flow` 行为与 1A 完全一致（回退到维护者草案，不是新开旁路） | 回滚安全 |
| K10 | 无 embedding 配置时降级为关键词检索并显式说明降级，不静默 | E01 |
| K11 | 文档正文只出现在 `role="user"` 的证据区且被定界符包裹；system 段与任何片段正文互不包含 | 注入 |
| K12 | 抽取调用不带工具（`tools` 为空），抽取链路上没有 `execute_sql` | 注入 |
| K13 | 模型输出里多塞 `source`/`evidence_ref`/`confirmed`/`sql` 等字段一律无效；`source` 恒由服务端设为 DOC，`evidence_ref` 恒由服务端生成，`missing` 由服务端按"必需键 − 幸存键"计算 | 注入 |
| K14 | `amend()` 拒绝非 USER 来源的规则（修 1A 缺口，§4.5.7） | 伪造来源 |
| K15 | value 中的每个数字 token 都必须出现在 quote 中，否则该规则被丢弃 | 断章取义粗筛 |
| K16 | 文档改动导致片段哈希变化**不**改变 `definition_hash`；它走 `check_refs` → EXPIRED 独立通道 | §4.5.4 |

**铁基线**：现有 345 passed / 1 skipped 必须保持全绿；`tests/test_metrics.py` 在分词器提取后行为不变。

---

## 6. 风险边界与回滚

### 6.1 回滚设计（整个切片是加法）

- 未配置 `knowledge:` 时 `flow` 走 1A 的 `MetricDraftBuilder`，行为逐字节不变（K9 就是钉这条）。**功能开关是配置存在与否，不是一个布尔 flag**——少一条容易忘记清理的分支。
- 四个子切片各自一个 commit，`git revert` 任意一个都不破坏前面的：revert 1B-3 后索引还在但没人用，revert 1B-2 后导入的文档只是磁盘上的文件。
- 失败回退点是 `v0.5.1` tag，它已经过远端 CI（Python 3.10 + 3.12）。
- 索引是独立 SQLite 文件（`.queryagent/knowledge.db`），删掉即回到无知识库状态，不影响 1A 的 `workflow.db`。

### 6.2 新增的安全面（必须写进 SECURITY.md，不能只在代码里处理）

SECURITY.md 现在把不可信输入枚举为三类：schema 注释、表内容、数据库错误消息。**文档是第四类，而且是最容易被普通员工写入的一类**——一个 Markdown 里就能藏"ignore previous instructions"。同时它开了一条**绕过全部三层防御的本地文件 I/O 路径**：读文档既不过 `safety.py`，也不过 Connector。

| 风险 | 处理 | 残余边界 |
|---|---|---|
| 路径逃逸读到凭据文件 | `sources[].path` 必须落在配置声明的目录内，导入时做 `Path.resolve()` 归一化与前缀校验，拒绝符号链接逃逸 | 配置本身写错目录仍会读到该目录下全部文件；导入时打印实际纳入的文件清单 |
| 文档注入改变系统行为 | §4.5 的结构性隔离；K4 做成确定性测试 | prompt 层提示只算缓解；注入仍可让确认单上出现一条误导性候选，靠人看出处识别 |
| 文档正文随 trace 落盘 | ADR-005 的"拒绝部分脱敏"论证是针对 SQL 结果行写的，没覆盖文档正文；需在 SECURITY.md 明说文档正文也会进 trace，并给出 `trace: false` 的指引 | 不做部分脱敏，保持与 ADR-005 一致的立场 |
| 第二把 API key 泄漏 | 只从 `QUERYAGENT_EMBEDDING_API_KEY` 读。**注意：现有的凭据键拒绝逻辑只在 `_load_llm` 内生效（`config.py:131`），不会自动覆盖新配置段**——必须把那段检查提成共用函数并显式应用到 `knowledge.embedding` | 检查的是键名黑名单，写成别的键名仍可能塞进凭据 |
| 文档正文外发给第三方 embedding 服务 | **必须在文档里显著说明**：启用云端 embedding 意味着企业文档内容会离开本机。这是接入方的数据处理边界决策，不是可以默认打开的选项 | 个人演示凭据不构成企业上线许可 |

### 6.3 已经过期的声明（顺手修正）

SECURITY.md 现写着 "This release does not provide the per-source total budgets, admission control or **human confirmation** required by the planned enterprise workflow."——确认门在 1A 已经落地，这句需要更新为"确认已提供，预算与准入控制仍未提供"。

### 6.4 明确不承诺

OCR 与扫描件、复杂版式还原、文档级主体白名单、增量同步与实时索引、reranker、
混合检索的权重调优、企业知识库供应商适配、跨用户共享的语义缓存、多副本部署。

关于引用，逐条列明**不承诺**：

- 不承诺语义蕴含校验——不保证 value 是 quote 的正确概括；
- 不承诺检测**断章取义**（引了适用条件的从句、丢了主句限定，看起来完全合规）；
- 不承诺检测**跨段合成**（只允许单段引用，模型可能被迫选到较弱那段）；
- 不承诺文档本身是对的（可能引用一段已废弃但仍在库里的口径）。

能写进 README 的只有 L0/L1：引用真实存在、本次检索到、已授权、逐字出自该段。
L2 只能写成"对不相关引用做了粗筛，最终判断由确认单上的原文与人完成"。

---

## 7. 文档与合规动作

| 动作 | 位置 | 说明 |
|---|---|---|
| 新 ADR-007 | `docs/adr/007-document-evidence-retrieval.md` | **收窄而非违反 ADR-002**：ADR-002 决定的是 5–50 条 metrics 的匹配方式，那个结论继续有效；ADR-007 决定的是文档证据检索这个新问题，并明确承诺：索引是本地文件不是服务、embedding 可选且缺省关闭、缺失时降级为关键词并说明。有先例可循（ADR-004 supersede 早期版本） |
| README 复核 | 第 7、27–43、57–58、347–351、362–363 行 | 尤其 "no vector store"、"Infrastructure \| none"、"不用向量库" 三处。改法是**限定**而不是删除：核心装机仍零向量库、零服务；语义检索是可选项 |
| SECURITY.md | 威胁模型、三层防御表、诚实边界、trace 四节 | 按 §6.2、§6.3 |
| CONTEXT.md | Seam map 的 Draft building 行 | 从"document-evidence impl is the next slice"改成已落地；新增 Knowledge 相关 seam 行与领域词条 |
| CHANGELOG | 只在 `[Unreleased]` 追加 | 历史条目一字不动 |
| prompt-log.md | 追加一条 | 规格 §六 DoD 强制项，**已欠 5 个版本**（最后一条停在 2026-08-19）。格式 `## YYYY-MM-DD · 切片 1B 文档证据检索`，正文含 动机 / 交付 / 关键决定 / 刻意没做 / 验证 |
| 本切片 spec | `docs/specs/workflow-slice-1b-2026-09.md` | 照 1A 的结构：计划先行、不变量表、模块职责表、关键设计决定、验收方法、**明确不承诺**；实现后补「实施结果 / 改掉的真实缺陷 / 仍未实现」 |

---

## 8. 评审原则与本地测试

### 8.1 评审时要盯的三件事

1. **权限是不是真的在检索前生效**——看 SQL 的 WHERE 子句，不是看返回后的 filter。这是 §10.4 的硬要求，事后过滤等于没做。
2. **每条 DOC 规则的引用是不是服务端验证过的**——特别要确认第 0 步的局部编号菜单没有被绕开（比如某处直接把全局 chunk id 暴露给模型）。
3. **有没有任何路径让文档内容改变状态、预算或执行**——`flow` 不能因为"检索不到证据"就回落到 agent 自由 SQL。`CONTEXT.md` 写的 "The gate is only worth anything if it cannot be walked around"。

按仓库既有做法跑双轴 review（Standards + Spec）。

### 8.2 测试组织（照抄 1A 的模板）

一层一个文件，外层不重复内层已证明的东西：

| 文件 | 层 | 依赖 |
|---|---|---|
| `tests/test_knowledge_loaders.py` | 解析：md / docx（stdlib 现造）/ 损坏文件 | 无 |
| `tests/test_knowledge_chunker.py` | 切片与定位 | 无 |
| `tests/test_knowledge_index.py` | 索引与 workspace 过滤 | tmp_path SQLite |
| `tests/test_knowledge_provider.py` | 三方法契约、撤权、变更检测 | tmp_path SQLite |
| `tests/test_evidence_extraction.py` | K1/K2 验证管线，手写 Stub 模型 | 无 |
| `tests/test_evidence_builder.py` | K6/K7 冲突与缺失归纳 | 无 |
| `tests/test_knowledge_end_to_end.py` | 真实语料 + 真实 SQLite 全链路，**只留一个测试** | demo 库，缺则 skip |
| `tests/test_cli_flow.py`（扩充） | 确认单上出现「文档依据」与出处；注入语料 K4 | tmp_path |

沿用的约定：模块 docstring 第一行写 `Slice 1B: <这层在证明什么>` 并点名与哪个文件分工；有编号的测试写一行 `"""K3/T06: 为什么这条重要"""`；测试名是完整英文陈述句且高频用 `X_rather_than_Y` 句式；时钟走依赖注入不 monkeypatch；固定角色 `ALICE`（ops）/ `MALLORY`（finance）；所有 `write_text`/`read_text` 显式 `encoding="utf-8"`；`pytest.raises` 必带 `match=`；拒绝路径一律配 `assert executor.executed == []` 这类副作用为零的断言。

### 8.3 本地验证顺序

```bash
cd /Users/sunweizhuo/Desktop/queryagent
PATH="$PWD/.venv/bin:$PATH" make test          # ruff + mypy + pytest，铁基线不得回退
```

```bash
.venv/bin/python -m queryagent.cli kb import --config examples/demo_ecommerce/config.sqlite.yaml
```

```bash
.venv/bin/python -m queryagent.cli flow "上个月新增用户有多少？" --config examples/demo_ecommerce/config.sqlite.yaml
```

人工验收看四件事：确认单上出现「文档依据」并带文件/章节/位置；两份冲突文档各自带出处并列；退款规则显示为缺失；换成 finance 身份检索不到 ops 的文档。

再跑一次注入语料和一次撤权场景，确认退出码 2 且未执行任何查询。

### 8.4 量化对照（1B-4，需要第二把 key）

```bash
.venv/bin/python eval/run_retrieval_check.py --output eval/results/retrieval-<日期>
```

固定一组合成电商文档与同义问句（如「新增用户」/「拉新数」/「新注册多少人」），报告：授权 gold 证据的 Recall@k（**分母只含该主体有权且适用的证据**）、引用定位正确率、无证据时的行为。关键词基线与语义检索分别报，**不合并成一个"RAG 准确率"**。

纪律：这组语料与 BIRD 的封存 test200 完全无关，不侵入、不读取；合成文档只描述**规则**不写死数字（demo 数据的日期相对今天生成，写死数字会过期）。

---

## 9. 开工顺序

1. 写 `docs/specs/workflow-slice-1b-2026-09.md`（本方案的仓库内版本，先行固定验收）
2. 1B-1 文档导入与切片 → commit
3. 1B-2 索引与授权检索 → commit
4. 1B-3 证据驱动草案 + ADR-007 + 文档整改 → commit（**产品价值在这一步落地**）
5. 1B-4 语义检索与对照（需第二把 key）→ commit
6. 双轴 review → 补 prompt-log → 视结果决定是否发 v0.6.0

前四步都不需要新 key，可以立刻开工。
