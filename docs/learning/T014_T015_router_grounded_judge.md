# T014-T015 Router 与 Grounded Judge：业务和设计学习笔记

## 1. 这组任务解决什么问题

T014-T015 处理模型生成 Finding 之后的两件事：

```text
Finding
→ 判断需要走哪条处理路径
→ 获取证据后重新判断原 Claim
```

它不负责真正调用订单 Tool 或 RAG 工具，也不负责完整工作流编排。

## 2. T014：Finding 粒度 Router

### 2.1 为什么在 Finding 粒度路由

同一段 Conversation 可能同时出现：

- 推诿；
- 售后解释错误；
- 无依据退款承诺。

不同 Finding 需要的证据不同。

因此不能因为一段会话里有一个问题需要查订单，就把整段会话都送去查订单。

### 2.2 Router 输入

```python
route_finding(finding: Finding) -> Route
```

只接收一个 Finding。

Router 读取：

```text
required_evidence
requires_external_verification
```

### 2.3 五种路径

```text
direct
order_context
business_knowledge
order_and_knowledge
human_review
```

对应关系：

| Finding 需求 | 路由 |
|---|---|
| 不需要外部证据 | direct |
| 只需要订单事实 | order_context |
| 只需要业务知识 | business_knowledge |
| 同时需要两类 | order_and_knowledge |
| 未知或无法处理 | human_review |

### 2.4 Router 不做什么

Router 不直接调用：

- Order Context Tool；
- Knowledge Tool；
- RAG；
- 模型。

它只返回“下一步应该走哪条路径”，具体执行由后续 Workflow 负责。

## 3. T015：Grounded Judge

### 3.1 为什么 Tool 返回不等于结论

订单查询返回：

```text
received_days = 12
```

知识检索返回：

```text
符合条件的商品支持七天无理由退货
```

这些只是事实。系统还需要判断：

```text
这些事实是否支持或推翻原 Claim？
```

这个过程叫 Grounded Judge。

### 3.2 Grounded Judge 输入

```python
judge(finding, evidence)
```

输入：

- 原 Finding；
- 原 Claim；
- 已有 Conversation Evidence；
- 已获取的订单/知识 Evidence。

### 3.3 Grounded Judge 输出

返回一条确认或修正后的 Finding。

它不能：

- 重新分析整段 Conversation；
- 自由查询数据库；
- 引入输入中没有的事实；
- 生成新的无依据结论。

### 3.4 为什么继续使用模型

判断“证据是否支持原 Claim”通常涉及语义推理。

例如：

```text
Claim：耳机十几天后仍可退货
订单：签收 12 天
知识：质量问题按审核结果处理
```

需要模型结合语义判断，不能只靠字符串比较。

但是要限制它的范围，只围绕原 Claim 和已有 Evidence 复判。

### 3.5 真实本地模型接入

Grounded Judge 使用的 `ModelClient` 可以直接传入：

```python
client = LocalQwenClient(max_new_tokens=1024)
judge = GroundedJudge(client)
```

真实 Case B 已验证：

```text
原 Finding
+ 订单证据 received_days=12
+ RAG 检索到的售后规则
→ Grounded Judge 返回修正后的 Finding
```

当模型输出被 Markdown JSON 代码块包裹时，仍通过统一的 `parse_json_output()` 解析。
## 4. 业务场景

### Case A：推诿

Finding：

```text
requires_external_verification = false
required_evidence = []
```

Router：

```text
direct
```

不需要调用工具。

### Case B：售后资格

Finding：

```text
required_evidence = [order_context, business_knowledge]
```

Router：

```text
order_and_knowledge
```

Workflow 获取订单和知识后，交给 Grounded Judge。

### Case C：退款承诺

Finding：

```text
required_evidence = [order_context]
```

Router：

```text
order_context
```

如果订单没有预计到账时间，Grounded Judge 应支持“无依据承诺”的判断。

### 未知证据类型

Router 不猜测，返回：

```text
human_review
```

避免系统自行编造新的处理路径。

## 5. 真实面试问题

### 问题 1：为什么 Router 要放在 Finding 粒度？

**回答：**

一段会话里可能有多个问题，每个问题需要的事实不同。按 Finding 路由可以只查询必要信息，减少无关 Tool 调用，也让路由准确率可以单独评测。

### 问题 2：为什么 Router 不直接调用工具？

**回答：**

路由决定“需要什么”，工具执行“去获取什么”。分开后可以独立测试路由、替换工具，并在 Tool 失败时走异常或人工分支。

### 问题 3：为什么已经有了证据还要 Grounded Judge？

**回答：**

证据只是事实，事实不一定直接等价于结论。Grounded Judge 负责判断事实是否支持原 Claim，但只允许基于已有证据，不能自由扩展。

### 问题 4：如何防止 Grounded Judge 自由发挥？

**回答：**

Prompt 中只提供原 Finding、Claim 和 Evidence，并明确禁止重新分析整段会话或引入新事实。输出仍然复用 Finding Schema，保证结果结构可控。

### 问题 5：如果证据不足怎么办？

**回答：**

应保留为不确定或转人工，而不是强行确认或否认。当前 T015 只定义复判输入输出，完整缺失证据路径将在 T016 工作流中处理。

## 6. 学习检查与答案

### 1. Router 输入什么？

单条 Finding。

### 2. Router 输出什么？

五种处理路径之一。

### 3. Router 为什么不能决定调用哪个 Tool？

它只负责判断证据需求，具体工具调用属于后续工作流职责。

### 4. Grounded Judge 输入什么？

原 Finding 和已经获取的外部证据。

### 5. Grounded Judge 为什么不能重新分析整段会话？

这会扩大判断范围，产生不可追溯的新 Claim，破坏证据约束。

### 6. 订单事实和知识证据能不能直接作为最终结论？

不能。它们只是事实依据，还需要判断是否支持原 Claim。

### 7. 未知证据类型如何处理？

转人工复核，不猜测。

## 7. 一句话总结

T014 根据单条 Finding 的证据需求决定处理路径，T015 只围绕原 Claim 和已有 Evidence 做受约束复判；两者把“路由”和“依据证据判断”分开，让 Agent 流程可控、可测、可解释。