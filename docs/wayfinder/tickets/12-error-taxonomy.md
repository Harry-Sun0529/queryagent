---
status: closed
type: task
blocked_by: []
claimed_by: fable-session
---
# T12 — CLI 错误三分类与退出码

## Question
现在所有失败都是退出码 2，把「用户配错了」「我的程序有 bug」「服务临时
抖动」混为一谈。脚本无法据此决定要不要重试；用户也无法据此判断该改配置
还是换 API。

## Work
按 sysexits 惯例三分：
- **2 = 用户错误**（缺 key、config 写错、路径不存在、缺可选驱动）——照
  现在的「问题 + 怎么修」输出。
- **70 = 程序缺陷**（EX_SOFTWARE，未预期的异常）——明确说这是 bug、
  请附 --verbose 的调用栈反馈，不要伪装成配置问题。
- **75 = 临时故障**（EX_TEMPFAIL，重试后仍 5xx/429、网络不可达）——
  提示稍后重试或换一个 base_url/供应商。

## Seams (tdd)
`main()` 级：每一类各一个测试，断言退出码 + 提示语 + 无 Traceback。

## Done when
- 三类测试绿；README/SECURITY 说明退出码含义。

## Resolution (closed 2026-08-19)

- `_explain` 现在返回 (问题, 怎么修, 退出码)，三分类：
  **2** 用户错误（缺 key、401、config 错、缺文件/驱动）、
  **70** EX_SOFTWARE 程序缺陷（明说是 bug、要 --verbose 调用栈，
  **不再伪装成配置问题**）、**75** EX_TEMPFAIL 临时故障（429/5xx/网络
  不可达，提示可重试或换 base_url）。
- 401 刻意归入用户错误而非临时故障——被拒的 key 不会自己变好，重试无意义。
- 4 个 seam 测试覆盖三类边界。
- **附带修掉一个 mypy 抓出的真 bug**：`_eval_public` 的 except 块用
  `done` 这个名字建了个 set，覆盖了外层的续跑映射，后续数据库再调
  `done.get()` 会 AttributeError。已改名并让降级结果也进增量日志。
