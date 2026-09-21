# T016 Agent State 与 Workflow：业务和设计学习笔记

## 1. T016 解决什么问题

T014 只负责判断一条 Finding 应该走哪条路径，T015 只负责拿证据复判。

T016 把它们和已有能力串成一条受控工作流：

```text
Conversation + Finding
→ 验证会话证据
→ Finding 路由
→ direct / order / knowledge / combined
→ Grounded Judge
→ 最终 Finding 或人工复核
```

T016 不实现数据库和 API，只负责工作流本身。

## 2. 为什么按单个 Finding 运行工作流

同一段 Conversation 可能产生多条 Finding：

```text
Finding A：客服推诿，不需要外部证据
Finding B：售后解释错误，需要订单和知识
Finding C：退款承诺，需要订单
```

如果按整段 Conversation 路由，就不得不把三条问题一起送进订单或知识流程。

正确方式：

```text
每条 Finding 单独运行一次工作流
```

这样每条问题只调用自己需要的工具。

## 3. AgentState 保存什么

```python
class AgentState(TypedDict, total=False):
    conversation
    finding
    route
    order_evidence
    knowledge_evidence
    final_finding
    status
    error
```

字段含义：

| 字段 | 作用 |
|---|---|
| conversation | 当前会话上下文 |
| finding | 当前正在处理的一条问题 |
| route | Router 决定的路径 |
| order_evidence | 订单工具返回的事实 |
| knowledge_evidence | RAG 返回的知识证据 |
| final_finding | 复判后的结果 |
| status | running / completed / human_review |
| error | 失败原因 |

State 只保存节点之间需要共享的数据，不保存模型对象、不保存数据库连接。

## 4. LangGraph 节点

### 4.1 verify

使用 T006 的 `verify_conversation_evidence()` 检查 Finding 引用的消息和原话。

如果证据不存在：

```text
→ human_review
```

否则：

```text
→ route
```

### 4.2 route

调用 T014 的 `route_finding()`。

输出：

```text
direct
order_context
business_knowledge
order_and_knowledge
human_review
```

### 4.3 direct

纯语义问题不需要外部事实。

直接把原 Finding 作为最终结果，状态为：

```text
completed
```

### 4.4 order

调用 Order Context Tool。

如果会话没有订单，或订单不存在：

```text
→ human_review
```

否则把订单字段转换成 `OrderEvidence`。

### 4.5 knowledge

调用 Knowledge Tool。

查询内容优先使用 Finding 的 `claim`，没有 Claim 时使用 `reason`。

如果没有检索到知识证据：

```text
→ human_review
```

### 4.6 combined

同时获取订单和知识证据。

任一步失败都进入人工复核，不继续用不完整证据复判。

### 4.7 judge

调用 T015 Grounded Judge。

输入：

```text
原 Finding
+ 订单 Evidence
+ 知识 Evidence
```

输出：

```text
final_finding
```

### 4.8 human

统一的人工复核出口。

清空最终 Finding，保留错误原因：

```text
status = human_review
```

## 5. 条件边如何工作

```text
verify
  ├── 证据有效 → route
  └── 证据无效 → human

route
  ├── direct → direct → END
  ├── order_context → order → judge
  ├── business_knowledge → knowledge → judge
  ├── order_and_knowledge → combined → judge
  └── human_review → human → END
```

工具节点之后：

```text
证据完整 → judge
证据失败 → human
```

Judge 之后：

```text
模型输出合法 → END
模型输出非法 → human
```

这就是受控工作流，不是让模型自由决定下一步。

## 6. 业务场景

### Case A：推诿

```text
Finding 无需外部证据
→ direct
→ 不调用订单和知识工具
```

### Case B：售后资格

```text
Finding 需要 order_context + business_knowledge
→ combined
→ 获取订单和售后规则
→ Grounded Judge
```

### Case C：退款承诺

```text
Finding 需要 order_context
→ order
→ 查询订单退款字段
→ Grounded Judge
```

### 订单不存在

```text
order tool 返回明确错误
→ human_review
```

### Knowledge 无召回

```text
knowledge tool 返回空列表
→ human_review
```

## 7. 真实面试问题

### 问题 1：为什么使用 LangGraph，而不是一串 if/else？

**回答：**

业务本身确实是条件路由，但 LangGraph 把 State、节点、条件边和结束节点显式表达出来，方便测试每条路径、观察中间状态，也方便后续增加人工分支和异常分支。它不是为了让流程自由，而是让受控流程结构化。

### 问题 2：为什么 State 不保存 Tool 和 Model 对象？

**回答：**

State 应该表示当前业务处理状态。Tool、数据库连接和模型对象是运行时依赖，应通过构建工作流时注入，不能混入业务状态，否则状态难以序列化和测试。

### 问题 3：为什么每条 Finding 单独运行一次工作流？

**回答：**

不同 Finding 需要不同证据。按 Finding 运行可以准确调用工具、记录路由和结果，也符合 ADR-004 的 Finding/Claim 粒度设计。

### 问题 4：Tool 失败为什么转人工而不是模型猜？

**回答：**

缺少订单或知识事实时，模型无法可靠判断。继续猜测会制造无依据结论，因此应保留错误并进入人工复核。

### 问题 5：为什么工作流仍然需要 Evidence verification？

**回答：**

Grounded Judge 只能处理真实证据。如果会话引用本身就不存在，先进入复判没有意义，所以必须在路由前验证 Conversation Evidence。

## 8. 学习检查与答案

### 1. T016 的输入是什么？

一条 Conversation 和一条或多条 Finding。

### 2. 为什么 State 使用单个 Finding？

每条 Finding 的证据需求和处理路径不同。

### 3. direct 路径为什么不需要 Judge？

它只依赖会话语义，没有外部 Claim 需要通过外部证据复判。

### 4. order 和 knowledge 失败后如何处理？

进入 human_review，并保留错误原因。

### 5. combined 为什么必须两类证据都成功？

Finding 明确要求订单和知识共同支持，缺少任一类都属于证据不完整。

### 6. final_finding 什么时候为空？

人工复核路径下为空。

### 7. T016 是否负责数据库保存？

不负责。持久化属于 T017。

## 9. 一句话总结

T016 用 LangGraph 把会话证据校验、Finding 路由、订单/知识取证、Grounded Judge 和人工复核串成单 Finding 受控流程；每条 Finding 独立处理，证据失败不猜测，工具和模型依赖不进入 State。