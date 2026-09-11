---
status: open
type: task
blocked_by: []
claimed_by:
---
# T49 — 调用链讲解与答辩

## Question

交接文档写着「用户还不能独立讲清核心调用链」「不把功能堆叠当作简历合格标准」。面试时能讲出
什么，取决于这一张票。

## Work

- `docs/walkthrough/flow-call-chain.md`：一次 flow 从敲回车到出数字，六个检查点（准备、证据、
  确认哈希、准入、编译与绑定、执行后说明），每一跳 `file:line` 与为什么。
- `agent-loop.md`：ReAct 路径与安全层。
- `qa-bank.md`：约 40 题设计取舍问答，每题锚到代码与 ADR，包括没做什么、为什么不保证。
- `demo-script.md`：3 分钟演示，附数据库没起来时的退路。
- 两轮模拟面试，每轮之后按暴露的缺口补文档；锚点检查脚本。

## Done when

- H15；能不看稿讲清 flow 调用链的六个检查点；两轮模拟面试的缺口都已补上。
