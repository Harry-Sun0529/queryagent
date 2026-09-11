---
status: open
type: task
blocked_by: [44, 45, 46]
claimed_by:
---
# T48 — 公开契约冻结与发布

## Question

语义化版本号从 1.0 起才真正有约束力。哪些东西冻结、怎样防止无意改动、怎样把包发出去？

## Work

- 冻结前的破坏性改名清单：只改确有歧义的名字。
- `tests/test_public_contract.py` + `tests/contract/*.json`：CLI 参数树、配置与映射文件的键、MCP
  工具 schema、`__all__`（新增 workflow 对外类型）。
- 0.6–0.9 写下的状态库 fixture，证明 1.0 可读。
- ADR-014：兼容与弃用策略（弃用项带警告保留一个小版本；状态文件只做向前迁移）。
- pyproject：描述、classifiers、urls、1.0.0；`.github/workflows/release.yml` 可信发布（OIDC）。
- TestPyPI 演练；干净 venv 的 wheel 冒烟；正式上传前维护者本人确认。

## Done when

- H12–H14；wheel 与 TestPyPI 安装都能跑 `queryagent --help` 与 SQLite 演示 flow。
