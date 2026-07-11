# HUMAN-OWNED 文件手写指导（开发期文档，v0.3.0 冻结时删除）

> 这份文档是"引导"，不是"答案"：只有概念讲解、决策清单和流程级伪代码，
> 没有可粘贴的实现。写不出来时可以让 AI review 你的代码、解释报错、
> 给某一步的伪代码提示，但不能让它替写（规格 §〇）。

## 推荐顺序与时间预算

1. **先写 `safety.py`**（约半天）：小、自包含、表驱动测试反馈快，适合热身。
2. **再写 `agent.py`**（约 1~1.5 天）：全项目最值钱的文件，写完你要能白板重现。

每完成一小步就跑测试，不要憋大招。激活测试的方法：删掉对应测试文件里的
`pytestmark = pytest.mark.skip(...)` 那一行。

```bash
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_safety.py -x        # -x 遇错即停
PATH="$PWD/.venv/bin:$PATH" pytest tests/test_agent_termination.py -k answer
PATH="$PWD/.venv/bin:$PATH" make test                             # 提交前全量
```

## Python 预备知识（10 分钟）

- **生成器**：函数体里出现 `yield` 后，调用它不会立刻执行，而是返回一个
  迭代器；消费者每 `for` 一次，函数体推进到下一个 `yield`。`run_agent`
  的返回类型 `Iterator[AgentEvent]` 就靠这个实现——你 `yield` 事件，
  demo/CLI 负责打印。函数中途 `return` 即结束流。
- **dataclass**：`Message(role="user", content="...")` 这样构造，
  `response.tool_calls` 这样取字段。本项目的事件、消息全是 frozen dataclass。
- **异常**：`try: ... except SafetyViolation as e: ...`；异常类名字符串可用
  `type(e).__name__` 拿到。
- **元组/字典相等**：`("execute_sql", {"sql": "..."}) == 上一轮的同款` 直接可比，
  死循环检测会用到。

---

## safety.py：SQL 白名单

### 心智模型

**白名单，不是黑名单**：不是"发现危险词就拦"，而是"只放行能证明安全的
形态"（单条 SELECT，允许 CTE），其余一律拒绝。为什么不用正则找 DELETE？
因为 `SELECT * FROM orders WHERE note = 'delete me'` 是合法查询——字符串
字面量里的关键词不该触发拦截。这就是必须用 sqlparse 做**词法分析**而不是
文本匹配的原因（面试必问点）。

### 第一步：在 REPL 里玩 sqlparse（20 分钟）

```bash
PATH="$PWD/.venv/bin:$PATH" python
```

逐个试这些，观察输出，做笔记：

```python
import sqlparse
stmts = sqlparse.parse("SELECT 1; DROP TABLE users")   # 几个 statement？
stmts[0].get_type()                                     # 返回什么？
sqlparse.parse("WITH t AS (SELECT 1) SELECT * FROM t")[0].get_type()  # CTE 呢？
sqlparse.parse("SELECT 1;")                             # 尾分号会不会多出空语句？
[t for t in stmts[0].flatten()]                         # token 长什么样
sqlparse.format("SELECT/**/1", strip_comments=True)     # 注释能被剥掉吗
```

**关键侦查任务**：`get_type()` 对 CTE、对注释开头的语句返回什么？如果不
可靠，你的兜底方案是什么（提示：找第一个有意义的 token，看它是不是
DML/DDL 关键字白名单里的 SELECT/WITH）？

### 你要拍板的规则设计（这是"你的"设计，写进注释里）

| 决策点 | 选项 |
|---|---|
| 注释怎么处理 | a) 含注释直接拒绝（测试表当前立场）b) strip 后再判 |
| 尾分号/空语句 | 过滤空 statement 再数条数，还是见分号就拒 |
| 大小写 | sqlparse token 已归一化吗？自己验证 |
| EXPLAIN / SHOW | 放行还是拒绝？（测试表未覆盖，你补 case） |
| 多层防御的分工 | 你的白名单管形态；超时/行数在 Connector；只读账号兜底 |

### 流程级伪代码

```
ensure_safe_select(sql):
    去空白；空串 → 拒绝
    sqlparse.parse(sql) → statements；过滤掉纯空白的 statement
    条数 != 1 → 拒绝（多语句注入）
    (按你的注释策略处理注释)
    判定唯一语句的类型是否为 SELECT（含 CTE）——用 get_type() +
        你的兜底方案双保险
    不是 → 拒绝
    拒绝 = raise SafetyViolation(理由, sql=原文)，理由要人话
```

测试表里的边界 case（如 `SELECT/**/1;DROP/**/TABLE users`）如果你的规则
立场不同，可以改表——但每处修改在 commit message 里写理由。

---

## agent.py：ReAct 主循环

### 心智模型（先画在纸上）

```
        ┌─────────── 每轮 ───────────┐
问题 → 组消息 → 问模型 → 有 tool_call？
                    │否 → AnswerEvent → 结束 ①
                    │是
                    ↓
              和上轮动作完全相同？→ 是 → ErrorEvent → 结束 ③
                    ↓否
              ToolCallEvent → 派发工具
                    │ SafetyViolation → ErrorEvent → 结束 ④
                    ↓
              ObservationEvent → 记入 history → 下一轮
        └── 轮数耗尽 → ErrorEvent/降级 → 结束 ② ──┘
```

四个带圈号的出口就是测试的四条终止路径。

### 数据流：history 里放什么

模型要"看见"自己上一轮干了什么、结果是什么，靠的是往 history 追加两条消息：

1. `Message(role="assistant", content=思考文本, tool_calls=(那个 ToolCall,))`
   ——模型自己的话原样存回去；
2. `Message(role="tool", content=observation.content, tool_call_id=对应 id)`
   ——工具结果，**tool_call_id 必须和 assistant 消息里的 ToolCall.id 配对**，
   否则 Anthropic API 会报错。

每轮开头用 `context_builder.build(question, history)` 重新组装全量消息。

### 流程级伪代码

```
run_agent(question, backend, registry, context_builder, max_turns):
    history ← 空列表
    上一轮动作 ← 无
    重复至多 max_turns 轮:
        messages ← context_builder.build(question, history)
        response ← backend.complete(messages, tools=registry.specs())
        若 response.text 非空 且 还有 tool_calls → yield ThinkEvent(text)
        若没有 tool_calls:
            yield AnswerEvent(response.text)；结束          # 出口①
        call ← tool_calls 里的第一个                        # 简化决策，见下
        本轮动作 ← (call.name, call.arguments)
        若 本轮动作 == 上一轮动作:
            yield ErrorEvent(死循环保护)；结束               # 出口③
        上一轮动作 ← 本轮动作
        yield ToolCallEvent(...)
        try: obs ← registry.validate_and_dispatch(call.name, call.arguments)
        except SafetyViolation as e:
            yield ErrorEvent(type(e).__name__, ...)；结束    # 出口④
        yield ObservationEvent(obs.content, obs.is_error, call.id)
        history 追加上面说的两条消息
    yield ErrorEvent(轮数上限) 或 降级直答                   # 出口②，你拍板
```

### 你要拍板的设计决策

- 一次响应带**多个** tool_calls 怎么办：只取第一个（其余轮次再来）还是
  全部执行？v0.1.0 建议取第一个，但把理由写进注释。
- 轮数耗尽时：ErrorEvent 还是拿现有信息降级直答？测试两者都接受。
- **解析失败**（text 为空且无 tool_calls，或 backend 抛 LLMParseError）：
  规格要求"带错误信息重试 1 次，再失败降级直答"。思路：捕获后往 history
  塞一条 user 消息说明解析失败，重试计数 +1；第二次失败就 yield 现有
  最好的回答。
- v0.1.1 的自修正（QueryError 观察喂回、上限 3 次、RetryEvent）现在
  **不写**，但你设计循环时给"哪里数重试次数"留个心眼。

### 卡壳时的自救顺序

1. 打印中间变量（临时 print 没关系，提交前删）；
2. 只跑一个测试：`pytest tests/test_agent_termination.py -k final_answer -x`；
3. 让 AI 解释报错/review 你的代码（不让它替写）；
4. 回看 `tests/fakes.py` ——FakeLLMBackend 的脚本就是"模型会怎么回话"的剧本。

### 完成后

- 删两个测试文件的 skip 行，全绿后 `make test`；
- 用你自己的身份 commit（这是面试可辩护性的物证链，规格 §六）；
- 对照 §七 防御清单第 1、2 条，试着不看代码把状态机画一遍。
