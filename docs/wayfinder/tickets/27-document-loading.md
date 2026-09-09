---
status: closed
type: task
blocked_by: []
claimed_by: opus-session-2026-09-09
---
# T27 — 文档导入与切片

## Question

把 Markdown 与 DOCX 变成带定位的片段，是后面一切的地基。这一张票不碰检索、
不碰持久化，只回答：一份文档进来，切成什么、每一片带什么定位信息、解析失败
时说什么。

关键约束：解析失败必须显式说"此资料未成功纳入"，**不能返回空文本假装没有
相关规则**（D20/K8）——否则用户会把"我们没读成功"误当成"文档没说"。

## Work

- `knowledge/models.py`：`Document` / `Chunk` / `EvidenceRef` / `Evidence` /
  `EvidenceHit` / `RefStatus`，全部 frozen dataclass。
- `knowledge/errors.py`：`KnowledgeError` 及子类。
- `knowledge/loaders/markdown.py`：标题层级 + 行号定位，stdlib。
- `knowledge/loaders/docx.py`：stdlib `zipfile` + `ElementTree` 解析
  `word/document.xml`；已验证可拿到标题层级与跨 `<w:r>` 拼接的文本，
  **不需要 python-docx**。
- `knowledge/loaders/__init__.py`：按后缀分派，PDF 走延迟导入。
- `knowledge/loaders/pdf.py`：optional extra `[docs]`，照 clickhouse 的六处
  模式（pyproject、mypy overrides、裸 import、工厂延迟导入、`cli._explain`
  分支、`monkeypatch.setitem` 测试）。
- `knowledge/chunker.py`：按章节与规则边界切片，保留相邻说明；表格不得把列
  标题与数值说明拆开。
- **归一化函数**（`text.py`）：NFKC、全角/半角统一、空白折叠、去零宽字符。
  这是纯函数，单独一组测试——引文匹配全靠它，中文场景最容易在这里出错。

## Seams (tdd, 先红后绿)

1. `load_document(path) -> Document`
2. `chunk_document(doc) -> tuple[Chunk, ...]`
3. `normalize(text) -> str`

## Done when

- md / docx / 损坏文件三条路径都有测试；docx fixture 用 stdlib 现造，零依赖。
- 每个 chunk 带来源文件、章节标题路径、位置、内容哈希。
- 解析失败抛 `DocumentParseError` 且消息指出是哪个文件、为什么。
- 归一化的中文用例：全角标点、软换行、零宽字符、DOCX 跨 run 拆字。
- `make test` 全绿，铁基线不回退。

## Resolution（2026-09-09）

三个 seam 全部红→绿：`normalize` / `load_document` / `chunk_document`。
377 passed / 1 skipped（基线 345，新增 32 个测试），ruff + mypy 51 文件通过。

**关键决定：切片边界跟着章节走，不跟 token 数走。** 一个横跨规则边界的切片会
让引用无法解析——读者分不清指的是哪一半；而把规则和它的限定句（「不含测试
账号」）切开，会改变规则本身的意思，且**看起来引用得完全合规**。章节边界是
作者已经替我们做过判断的地方。

**归一化的取舍写进了代码注释**：中日韩字符之间的换行整个删掉（DOCX/PDF 提取
会在句中插软换行，不删则引文永远匹配不上），拉丁词之间保留单空格（否则
"paid orders" 会粘成 "paidorders"，而归一化后的文本正是要展示回给用户的）。
判据是"两侧邻居是否都为中日韩字符"。

**实施中发现并修掉的真缺陷**：标题与正文被归一化粘成 `新增用户口径运营口径按…`。
它有两重危害——作为引文上下文展示时不可读，以及**在边界处制造出任何文档里都
不存在的子串**，而引用校验会痛快地确认它。改为用冒号（内容，不是空白）分隔。
这个 bug 只有把真实 md/docx 跑通、把文本打出来看才会暴露，单测断言子串是看
不出来的。

**PDF 走 optional extra**，照 clickhouse 的既有六处模式；扫描件只有页面没有
文本层时抛 `DocumentParseError` 而不是返回空文档——"我们没读成功"和"文档没
提这条规则"是两个不同的断言（K8）。

后续票据依赖的事实：`Chunk` 带 `chunk_id`（跨重载稳定）、`content_hash`
（逐切片，改一节不会让其余切片失效）、`section_path`、`start/end` 与 `unit`
（line/paragraph/page 三种坐标系）。
