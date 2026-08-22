---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T20 — 版本号单一来源与依赖上界

## Question
`queryagent.__version__` 说 0.1.0，`pyproject.toml` 说 0.4.0——两处会各自
漂移。而 anthropic 无上界刚让 CI 在代码没变的情况下变红。

## Work
- `__version__` 改为从包元数据读取（`importlib.metadata`），消除第二处
  事实来源。
- 给其余运行时依赖加上界（httpx / sqlparse / PyMySQL / PyYAML /
  clickhouse-driver），并在注释里写明理由与复查方式。

## Seams (tdd)
`queryagent.__version__` 与已安装的包元数据一致。

## Done when
- 测试绿；`pip install -e .` 后版本号自洽。

## Resolution (closed 2026-08-22)

- `__version__` 改为 `importlib.metadata.version("queryagent")`，源码树里
  没装包时降级为 `0+unknown`——**第二个事实来源消失了**（此前它停在 0.1.0
  而 pyproject 已是 0.4.0）。
- 全部运行时依赖加上界：httpx<1、sqlparse<1、PyMySQL<2、PyYAML<7、
  clickhouse-driver<1，注释写明理由——**抬高上界是一个需要跑测试的
  主动动作，不是默认行为**。
