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
