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
