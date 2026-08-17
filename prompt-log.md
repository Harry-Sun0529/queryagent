# Prompt Log

规格 §六 DoD 要求：记录每个版本的关键 prompt 迭代与人机协作决定。

## 2026-07-11 · v0.1.0 脚手架（第一个周末开工）

- **输入**：《QueryAgent 工程规格（Claude Code 执行版）rev2》全文 + 指令
  「按 plan 建仓库、init git、开始第一个版本」。
- **Claude Code 产出**：全部 AI-OWNED / AI-ASSISTED 骨架 —— pyproject、
  Makefile、CI、events/errors/schema/config、llm/base +
  anthropic_backend、connectors/base + mysql、demo 造数脚本（方言无关
  IR）、docker-compose、FakeLLMBackend、全部单测；tools.py 与 context.py
  为 AI-ASSISTED-R 初版（含 REVIEW-ME 决策点，待人类实质重构后方可视为合入）。
- **HUMAN-OWNED 边界执行情况**：`agent.py`、`safety.py` 只写了接口签名 +
  验收 checklist docstring，实现留白（NotImplementedError）；对应验收测试
  已写好并整模块 skip，人类实现后删掉 skip 行即可跑。
- **关键决定**（详见各 commit 描述）：
  - demo MySQL 用 8.0 镜像 + `mysql_native_password`，避免 PyMySQL 对
    caching_sha2_password 的 `cryptography` 传递依赖（规格 §四 依赖极简）。
  - config 为单数据源结构（规格 §三 v0.1.1 验收是"同一 config 分别指向
    不同库"，即改配置切换而非同时多源）；数据源列表如有需要 v0.4+ 再议。
  - 配置校验错误用 ValueError，不扩充规格 §二 冻结的异常层级。
  - 造数脚本日期相对"今天"滚动、RNG 固定种子：demo 问题永远非平凡，
    数据形状可复现。

## 2026-07-11 · v0.1.1 AI 侧预推进（同日下午）

- **动机**：用户要求在 Fable 5 可用窗口内尽量多推进 AI 侧工作。
- **产出**（按规格 §三 v0.1.1 版本内优先级）：metrics/base.py +
  yaml_store.py（AI-ASSISTED-R 初版，3 个 REVIEW-ME）、examples/metrics.yaml
  格式脚手架（内容 TODO 归人类）、SQLite connector（progress-handler 超时）、
  OpenAICompatibleBackend（httpx 手写，不引 openai 包）、cli.py（含
  ClarifyEvent 预留分支）、造数脚本 SQLite 发射器、connector/backend 工厂、
  docs/handwriting-guide.md（HUMAN 文件伪代码级引导，v0.3.0 冻结时删）。
- **刻意没做**：context.py 预算裁剪（AI-ASSISTED-R 规则：人类重构 commit
  之前不叠加改动）；agent.py 自修正与追问（HUMAN-OWNED）；ClickHouse
  connector（§八 第一砍单项，且无环境无法验证，不写未经测试的代码）；
  eval runner（依赖 agent 语义定稿）；metrics 注入 context 的接线（同受
  R 规则阻塞，等人类重构后进行）。
- **关键决定**：OpenAI 兼容协议 tool-call 的 arguments 是 JSON 字符串，
  在 backend 内 json.loads 消化，坏 JSON 抛 LLMParseError；SQLite 用
  set_progress_handler 做 deadline 中断（SQLite 无原生查询超时）；CJK
  匹配用字符 bigram 做零依赖分词替代。

## 2026-07-11 · v0.2.0 eval 体系预推进 + 三方言真实验证（同日晚）

- **动机**：继续利用 Fable 5 窗口，把"可信"做实——能测的全部真测。
- **eval 体系**（规格 §三 v0.2.0 AI 侧）：queryagent/evals 包
  （compare/cases/runner/public）+ `queryagent eval` 子命令
  （--backend/--model 双模型、--public 公开子集模式）+ make eval。
  runner 只消费事件流（不 import agent.py），所以在 agent 落地前就有
  31 个单测覆盖。eval 代码进包（pip install 后可用）、数据留 repo 根
  eval/ 目录——对规格路径的偏差，理由是打包需求。
- **真实验证**（Docker）：MySQL demo 容器端到端 5 项集成测试全过——
  含只读账号拦 INSERT（SECURITY.md 第三层防御的实证）与 v0.1.0 验收
  问题的非平凡答案；ClickHouse connector 落地并对 24.8 容器 4 项全过
  （§八 第一砍单项在没有占用周末预算的情况下提前完成）。集成测试探测
  不到容器时自动 skip，CI 不受影响。
- **踩坑记录**（面试素材，§七 数据轨第 11 条）：CH 官方镜像 default
  用户仅限容器内 localhost，宿主机连接需 CLICKHOUSE_USER 建用户；
  PyMySQL ping(reconnect=True) 已弃用，改 ping(False)+换新连接；CH 行数
  截断用 result_overflow_mode='break' 服务端截断 + 客户端精确 re-cap。
- **cases.yaml 双关**：内容（20 条）仍归人类；已放 5 条可直接对
  demo_shop 跑的格式示例。CHANGELOG.md 与 SECURITY.md 草稿一并就位
  （SECURITY 是 v0.3.0 项，提前起草，等人类 review）。

## 2026-08-17 · 协议转折与 v0.1.0 发布

- **所有者决定**：时间紧迫（距投递窗口过近），项目所有者显式解除了
  §〇 的 HUMAN-OWNED 限制，委托 AI 完成 agent.py 与 safety.py 的实现、
  全部 AI-ASSISTED-R 决策点的定稿，以及原属人类的内容项（metrics.yaml
  六条口径、eval 20 条用例）。本日志如实记录这一转折——这个项目由 AI
  深度参与构建，架构决策与验收标准来自人类撰写的工程规格。
- **实现落地**：safety.py（词法级白名单：单语句 + 首 token + 类型 +
  禁用关键字四重校验，INTO OUTFILE / FOR UPDATE 一并拦截）；agent.py
  （四终止条件 + 解析失败重试一次后降级直答 + 自修正上限 3 次 +
  ask_clarification 工具拦截转 ClarifyEvent）；context.py 完成口径注入、
  追问触发指引与 token 预算裁剪（成对裁最旧历史，防孤儿 tool 消息）。
- **验证**：153 个测试全绿（原 24 个 skip 的验收测试全部激活通过；
  9 个对真实 MySQL/ClickHouse 容器的集成测试；20 条 eval 用例的参考
  SQL 逐条对 demo 库执行验证）。发现并修复宿主机与 Docker VM 时钟不一致
  导致的日期窗口断档（测试改为以数据自身 max(created_at) 锚定）。
- **发布**：版本 0.1.0，推送至 github.com/Harry-Sun0529/queryagent。
  README 如实标注：eval 准确率数字待真实 LLM 端点跑出后发布。
