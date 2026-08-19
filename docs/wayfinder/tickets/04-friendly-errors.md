---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T4 — 友好错误提示

## Question
实测四类新手错误全部吐 Python traceback（消息内容其实不错，但没人接住）。

## Work
CLI 顶层捕获并转成「一行问题 + 一行怎么修」，退出码 2：
- 缺 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` → 提示 export 哪个变量
- HTTP 401 → 提示 key 无效，检查是否用错后端的 key
- config 路径不存在 → 提示路径与示例 config 位置
- `ModuleNotFoundError: clickhouse_driver` → 提示
  `pip install -e ".[clickhouse]"`（当前最差的一条：完全没线索）
- 数据库文件不存在 → 提示先 `make demo-data`
`--verbose` 时仍打印完整 traceback（调试需要）。

## Seams (tdd)
CLI `main()` 级测试：每类错误断言退出码 2 + stderr 含修复提示 + 不含
"Traceback"。

## Done when
- 五类测试绿；真机复跑第一次实测的四条错误路径，输出可读。

## Resolution (closed 2026-08-19)

- `main()` 顶层统一捕获，`_explain()` 把异常映射成「一行问题 + 一行怎么修」，
  退出码 2；`--verbose` 时仍打完整 traceback（调试不受损）。
- 覆盖：缺 key（给出 export 命令）、401（提示检查 backend/base_url 匹配）、
  config 不存在（指向示例目录）、库文件不存在（提示 make demo-data）、
  缺可选驱动（给出 pip install 命令）、配置值非法。
- 5 个 CLI 级测试（走 `main()`，断言退出码 + 提示文本 + **不含 Traceback**）。
  踩坑：缺驱动那条在全量套件里会被其他测试的 import 污染，需同时从
  sys.modules 摘掉 connector 模块，惰性导入才会重新执行。
- 真机复测四条路径，输出均为两行可读提示。
