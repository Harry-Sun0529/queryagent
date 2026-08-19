# dev 集失因分析（BIRD mini-dev，seed 7，30 题）

模型 deepseek-v4-flash，temperature 0，2026-08-19。基线：首次 7/30 (23%)、
自修正后 10/30 (33%)。20 个失败全部是「结果集不同」——没有崩溃、没有超时、
没有 SQL 语法错误，说明 agent 能稳定产出可执行的 SQL，问题在语义与形状。

逐题比对 gold SQL 与 agent SQL 后，20 个失败分为三类：

## A 类 · 投影不匹配（10/20，50%）——**值算对了，形状不对**

agent 像个乐于助人的分析师，把上下文列一并返回；BIRD 按结果集精确比对，
于是「对的答案」被判错。

| case | 问题 | gold | agent |
|---|---|---|---|
| card_games_358 | 某张卡的边框颜色 | `black`（1 列 1 行） | `name, borderColor`（2 列 4 行，无 DISTINCT） |
| european_football_2_1079 | 最高的球员是谁 | `Kristof van Hout` | `player_name, height` |
| card_games_415 | 无内容警告的占比 | `100.0` | `total, no_warning, 100.0` |
| financial_189 | 账户号 | `1743` | `1743, client_id, birth_date, salary` |
| codebase_community_539 | 帖子作者是谁 | `csgillespie` | `post_id, title, csgillespie` |

（另有 california_schools_85、card_games_345/480、codebase_community_707、
toxicology_268 同型。）

**这是可修的，且修法是通用原则而非针对题目**：系统提示补一条「只 select
问题所要的东西，不要附带标识列或上下文列；问『有哪些值』时用 DISTINCT；
上下文写进回答文字，不要写进 SELECT 列」。

**修复效果（dev 复跑）**：首次 23% → 30%，自修正后 **33% → 47%**。
自建集 gate 同时复跑两次未回退（自修正后 17-18/18、追问 4/4）。

## B 类 · 金标本身有争议（5/20，25%）——**不可修，也不该修**

- `thrombosis_prediction_1252 / 1256`：问「有多少病人」，gold 写
  `COUNT(T1.ID)` 且在三表 join 之后——数的是 join 后的**行数**，不是去重
  病人数。agent 用 `COUNT(DISTINCT ...)`，答 1 / 25，gold 是 4 / 208。
  按中文语义 agent 更对，按基准 agent 错。
- `codebase_community_685`：「Name the user who posted it last time」——
  gold 取 `LastEditorUserId`，agent 取 `OwnerUserId`。英文本身歧义。
- `formula_1_906`：Hamilton 首站积分，gold 取 `driverStandings.points`
  （14.0，累计分），agent 取 `results.points`（8.0，单场分）。两个数据源
  都合理，问题没指明。
- `formula_1_955`：「champion」按年度冠军还是末站冠军，定义不同。

这类恰恰是本项目**口径治理**要解决的问题：同一个问题、不同口径、不同答案。
在没有口径声明的公开基准上，agent 只能猜；在有 `metrics.yaml` 的场景里，
它会按声明执行，或在冲突时反问。这是把基准失败转成产品论证的一处。

## C 类 · 真正的语义错误（5/20，25%）

- `california_schools_72`：绕了 5 轮探索，最终没产出答案查询。
- `card_games_412`：漏掉 `layout` 与 `borderColor` 两个过滤条件。
- `debit_card_specializing_1481`：年均消费差的算法与 gold 完全不同。
- `financial_169`：增长率 25.36 vs 25.30——分母口径细微差异。
- `card_games_407`：把「德语的卡牌类型」理解成了外文名里的类型串。

这类是模型能力上限（多跳 join、复杂聚合的口径细节），prompt 改不动，
需要更强模型或更多脚手架。对照 T5 的双模型数据：v4-pro 在自建集上首答率
高 15pp，说明这类正是强模型的优势区间。

## 结论

- **一半的「失败」不是算错，是没按要求的形状回答**——这在真实产品里几乎
  不算问题（用户读的是回答文字），在基准上却全额扣分。修掉它既提升分数
  也让输出更克制。
- **四分之一是基准自身的口径歧义**，无法也不应修；它们反过来论证了口径
  声明的价值。
- **剩下四分之一才是真正的能力差距**，其中多跳 join 与复杂聚合是弱模型的
  软肋，与双模型对比的结论一致。
