---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T19 — 给「库」一个真正的公开 API

## Question
README 的对比表写着 `Form factor: library`，卖点是"给工程师的一个 pip 包"，
但 `from queryagent import *` 拿到的是空的——用户必须先读懂内部模块结构
才能用。**这是声明与实现之间最直接的落差。**

## Work
在 `queryagent/__init__.py` 导出最小可用面：`run_agent`、事件类型、
`load_config`、`make_connector`、`make_backend`、`ContextBuilder`、
`ToolRegistry`/`make_default_tools`、异常层级。`__all__` 显式列出。
README 加一段「作为库使用」的最小示例。

## Seams (tdd)
1. `from queryagent import run_agent, AnswerEvent, load_config` 可用。
2. README 里的库用法示例能真的跑通（用假后端，不打网络）。

## Done when
- 两个 seam 测试绿；README 的库示例是被测试过的代码，不是想象出来的。

## Resolution (closed 2026-08-22)

- `queryagent/__init__.py` 导出最小可用面并显式 `__all__`：`run_agent`、
  九种事件、`ContextBuilder`/`ToolRegistry`/`load_config`/`make_backend`/
  `make_connector`/`make_default_tools`/`YamlMetricStore`、异常层级。
- README 新增「Using it as a library」段，**该段代码由
  `tests/test_public_api.py` 实际执行**——没跑过的示例代码正是一个库第一
  印象崩掉的方式。
- 5 个 seam 测试，包括 `__all__` 里每个名字都真实存在。
