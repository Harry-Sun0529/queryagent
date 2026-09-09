# 切片 1A：持久化草案与强制确认门

日期：2026-09-09。状态：计划（本文件先于实现写成，验收标准在实现前固定）。

## 1. 这一刀切什么

交接文档 §16 阶段1 的第一刀：**先立可信执行边界，再补 RAG**。

本切片交付一条真实链路：

```text
prepare(可信身份, 问题) → DefinitionDraft(v1)
      → [缺失规则] amend(用户补充) → Draft(v2)
      → confirm(draft_id, version, definition_hash) → Confirmation
      → execute(confirmation_id, idempotency_key) → QueryRun → 结果
```

**不在本切片内**：RAG 检索与文档证据（1B）、通用 QueryPlan 编译器与结果解释（1C）、
历史沿用（1D）、统一预算（1E）、MCP/Web（阶段2）。

## 2. 必须由程序保证的不变量

对应交接文档 §9.2 与 §17.2 验收矩阵。

| 编号 | 不变量 | 对应 T |
|---|---|---|
| I1 | 没有有效 Confirmation 时，业务 SQL 执行次数为 0 | T01 |
| I2 | 问题本身已经很明确，也仍然产出待确认草案 | T01 |
| I3 | 调用方参数里的 `confirmed=true` / `subject_id` 不被采信；确认记录只能由服务端 `confirm()` 产生 | T09 |
| I4 | 确认绑定 draft_id + version + definition_hash；草案改版后旧确认不能执行 | T10 |
| I5 | 语义字段变化必然产生新版本与新 hash | T11 |
| I6 | 并发修改用 expected_version 乐观锁，后写不静默覆盖 | T12 |
| I7 | 相同 idempotency_key 的重复执行返回同一个 run，不再次执行业务 SQL | T13 |
| I8 | 跨主体访问草案/确认/run 一律拒绝，且不泄露存在性以外的内容 | T06 |
| I9 | 状态由服务端持久化；进程重启后草案/确认/run 状态可恢复 | T27 |
| I10 | 维护者未配置映射的口径不编译、不猜表，直接失败 | T14 |

## 3. 模块与职责

新增包 `queryagent/workflow/`，不改动现有 `agent.py` / `tools.py` 的既有行为。

| 文件 | 职责 |
|---|---|
| `models.py` | ActorContext、Rule/RuleSource、BusinessDefinition、DefinitionDraft、Confirmation、QueryRun 及状态枚举；hash 计算 |
| `errors.py` | ConfirmationRequired、StaleVersion、PermissionDenied、WorkflowStateError、MappingNotFound |
| `store.py` | `SqliteWorkflowStore`：草案/确认/run 的持久化与乐观锁、幂等键唯一约束 |
| `builder.py` | `MetricDraftBuilder`：从维护者 metrics 生成候选口径与缺失字段（1B 会换成带证据的实现） |
| `compiler.py` | `TemplateCompiler`：维护者配置的 口径→SQL 模板；无映射即报错，不猜 |
| `service.py` | `QueryWorkflow`：prepare / amend / confirm / execute 的状态推进与全部准入检查 |

`ActorContext` 只能由可信入口（CLI 本地用户、未来 Web 会话、MCP 宿主）构造，
不从模型输出或工具参数中解析。这是 D11 的落点。

## 4. 关键设计决定

**为什么确认绑 hash 而不只绑 version**：版本号可以被回放，hash 保证"用户看到的语义"
与"执行的语义"逐字节一致（§9.2 不变量 4、5）。

**为什么执行前再查一次**：确认与执行之间可能发生撤权、草案改版、过期（§9.2）。
`execute()` 重新读库校验，不信任调用方回传的对象。

**为什么 1A 用模板编译器**：D09 要求映射由维护者定义。通用 QueryPlan 是 1C 的工作；
1A 用最小的维护者模板表证明"未配置映射就不执行"这条边界，避免为了跑通而放开自由 SQL。

**为什么用 SQLite**：§19 第 4 项未选型；本切片按"本地单进程"实现并在文档中声明该边界，
不宣称企业高可用方案。

## 5. 验收方法

行为测试（FakeLLM 不参与；本切片不调用模型）：

1. `tests/test_workflow_models.py`：hash 稳定性、语义字段变化改变 hash、规则来源标注。
2. `tests/test_workflow_store.py`：乐观锁冲突、幂等键唯一、跨主体读取拒绝、重开 store 后状态恢复（I9）。
3. `tests/test_workflow_service.py`：I1–I10 逐条，业务 SQL 用计数替身，断言未确认路径计数为 0。
4. 端到端：真实 SQLite `examples/demo_ecommerce/demo_shop.db`，新增用户两种口径分别确认执行，
   结果与直接 SQL 校验一致。

全量 `ruff` + `mypy` + `pytest` 必须继续通过（基线 305 passed / 1 skipped）。

## 6. 明确不承诺

- 不承诺权限模型完整：1A 只有 subject/workspace 级别归属检查，文档 ACL 是 1B。
- 不承诺预算：1E 之前，执行次数没有全局上限。
- 不承诺多副本：状态在单进程 + 本地 SQLite，多副本需共享协调后另行验收。
- 不承诺自然语言解释质量：1A 的呈现是结构化字段，通俗解释是 1C。

---

## 7. 实施结果（2026-09-09）

状态：**已实现并通过本地验收**。未提交、未推送、未发版。

### 交付内容

| 文件 | 说明 |
|---|---|
| `queryagent/workflow/models.py` | ActorContext、Rule/RuleSource、Candidate、BusinessDefinition、Draft/Confirmation/Run 及状态枚举 |
| `queryagent/workflow/errors.py` | 六种可区分的拒绝 |
| `queryagent/workflow/store.py` | SQLite 存储；乐观锁、幂等键唯一约束、按 subject 归属检查 |
| `queryagent/workflow/builder.py` | 从维护者 metrics 生成候选与缺失字段 |
| `queryagent/workflow/compiler.py` | 维护者映射表；无映射即 MappingNotFound |
| `queryagent/workflow/mappings.py` | 映射文件加载与校验 |
| `queryagent/workflow/execution.py` | 连接器执行器（经 safety 白名单） |
| `queryagent/workflow/render.py` | 口径确认单与结果口径回述 |
| `queryagent/workflow/service.py` | QueryWorkflow：prepare / amend / confirm / execute |
| `queryagent/cli.py` | 新增 `flow` 子命令与按类型的拒绝补救提示 |
| `queryagent/config.py` | 新增 `workflow.mappings_path` / `workflow.state_path` |
| `queryagent/metrics/base.py`、`yaml_store.py` | 新增可选 `variants:`（必填字段未变） |
| `examples/metrics.yaml`、`examples/query_mappings.yaml` | 合成电商演示数据 |

### 验收结果

- `tests/test_workflow_models.py`（9）、`test_workflow_store.py`（8）、
  `test_workflow_service.py`（15，逐条覆盖 I1–I10）、`test_workflow_end_to_end.py`（1）、
  `test_cli_flow.py`（7）。
- 全量：`ruff` 通过、`mypy` 42 源文件通过、`pytest` **345 passed / 1 skipped**
  （基线 305/1；唯一 skip 仍是本地缺 BIRD 原题文件）。
- 真机演示（SQLite `demo_shop.db`）：同一问题「上个月新增用户有多少？」，
  注册口径 47635、首单口径 28695；不选口径、不确认两条路径均退出 2 且未执行任何查询。

### 实施中改掉的两处真实缺陷

1. 确认单上「口径说明」写着"（注册口径）"，而「选定口径」可能是首单口径——
   用户被要求确认一份自相矛盾的单子。改法是把分歧从 `definition` 移入 `variants`，
   并按维护者原话渲染选定项，而不是显示 `first_order` 这种查表键。
2. 候选口径的文案原本不进内容哈希。用户是照着这段文案做的选择，
   改文案却不使确认失效。已纳入哈希并补测试。

### 仍未实现（不要据本切片宣称）

RAG 与文档证据、文档级 ACL、历史沿用、统一预算与并发控制、MCP、Web、
多副本部署、通俗自然语言解释。1A 的 provenance 目前只会出现
「系统映射」和「本次约定」——「文档依据」要等 1B 的检索证据才会真正产生。
