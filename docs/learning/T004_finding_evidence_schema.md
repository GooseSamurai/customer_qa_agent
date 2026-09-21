# T004 Finding 与 Evidence：业务和设计学习笔记

## 1. 这份文档讲什么

T004 解决的是：

```text
客服质检发现问题后，如何表示一条问题，以及支持这条问题的证据如何表示？
```

它只定义数据结构，不实现：

- 判断是否应该查询订单；
- 调用订单接口；
- 检索业务知识文档；
- 验证原话是否真的存在；
- 人工复核；
- 模型调用。

这些内容属于后续任务。

## 2. 核心业务对象

### 2.1 Conversation 和 Finding

Conversation 是一次完整客服接待，Finding 是从这次接待中发现的一条具体问题。

关系是：

```text
Conversation 1
    └── Finding 0..N
```

一次会话可能没有问题，也可能同时存在多个不同问题：

```text
Conversation
├── Finding：客服推诿客户
├── Finding：业务解释错误
└── Finding：无依据承诺
```

因此 Finding 是独立单位，不能把多个问题强行合并成一个大标签。

### 2.2 Finding 和 Evidence

Finding 是“发现了什么问题”，Evidence 是“为什么能得出这个发现”。

例如：

```text
Finding：客服可能存在错误解释售后规则
Evidence：
    客服原话：超过 7 天都不能退
    订单事实：商品签收 12 天
    业务知识：符合条件商品支持七天无理由退货
```

Finding 不能只有结论，还要有可以追溯的依据。

## 3. Finding 的字段

```python
class Finding(BaseModel):
    rule_id: str
    risk_type: str
    severity: RuleSeverity
    reason: str
    conversation_evidence: list[ConversationEvidence]
    requires_external_verification: bool
    claim: str | None = None
    required_evidence: list[RequiredEvidence]
    external_evidence: list[ExternalEvidence] = []
```

### `rule_id`

对应哪一条企业质检规则。

作用：把问题和规则关联起来，方便追踪规则版本和后续统计。

### `risk_type`

问题类型，例如：

```text
blame_shifting
policy_explanation_error
unsupported_promise
```

它描述问题类别，不描述具体原因。

### `severity`

问题严重程度，复用 QARule 中的：

```text
low
medium
high
```

这样规则和问题使用同一套等级，避免出现不同写法。

### `reason`

对问题的文字说明。

它解释“为什么认为这里有问题”，不是证据本身。

### `conversation_evidence`

来自客服会话的证据。

至少保留一条，因为没有任何原始会话依据的 Finding 无法追溯。

### `requires_external_verification`

表示这条 Finding 是否还需要查询订单、业务知识等外部证据。

它只表示“需要或不需要”，不负责决定去查什么。

### `claim`

需要核验的具体事实或说法。

例如：

```text
耳机购买十几天后是否可以退货
```

纯语义问题可以没有 Claim，因此允许为空。

### `required_evidence`

表示需要哪些外部证据。

当前只允许两种：

```text
order_context
business_knowledge
```

空列表表示不需要外部证据；如果不需要外部证据，就不应该填写其他值。

### `external_evidence`

后续查询订单或业务知识后，把结果放在这里。

Finding 最初由模型产生时，外部证据通常还没有，因此默认为空列表。

## 4. 三类 Evidence

### 4.1 ConversationEvidence

来自客服原话：

```python
class ConversationEvidence(BaseModel):
    message_id: str
    quote: str
```

- `message_id`：定位具体是哪条消息；
- `quote`：具体引用了哪段原文。

T004 只保存这两个值，不检查原文是否真实存在。真实性检查属于后续证据校验。

### 4.2 OrderEvidence

来自订单上下文：

```python
class OrderEvidence(BaseModel):
    order_id: str
    field: str
    value: Any
    queried_at: datetime
```

- `order_id`：事实来自哪个订单；
- `field`：查询了哪个字段；
- `value`：字段值；
- `queried_at`：什么时候查询的。

`value` 使用通用类型，是因为订单字段可能是数字、字符串、布尔值、空值或嵌套结构。T004 只负责承载，不解释具体业务含义。

### 4.3 KnowledgeEvidence

来自业务知识文档：

```python
class KnowledgeEvidence(BaseModel):
    source_id: str
    chunk_id: str
    text: str
    metadata: dict[str, Any] = {}
```

- `source_id`：文档来源；
- `chunk_id`：具体文档片段；
- `text`：片段内容；
- `metadata`：版本、生效时间等附加信息。

T004 只保存知识片段，不负责检索和校验版本是否有效。

### 4.4 外部证据的两种类型

```python
ExternalEvidence = OrderEvidence | KnowledgeEvidence
```

意思是：外部证据可以是订单事实，也可以是业务知识片段中的任意一种。

## 5. 四种处理表达

`required_evidence` 和 `requires_external_verification` 共同表达后续需要做什么。

| 场景 | `required_evidence` | `requires_external_verification` |
|---|---|---|
| 纯语义问题 | `[]` | `False` |
| 需要订单事实 | `[order_context]` | `True` |
| 需要业务知识 | `[business_knowledge]` | `True` |
| 同时需要两类 | `[order_context, business_knowledge]` | `True` |

如果两者表达不一致，Finding 会被拒绝：

```text
需要外部核验，但没有 required_evidence
不需要外部核验，却填写了 required_evidence
```

这样可以避免后续流程不知道该走哪条路。

## 6. 为什么这样设计

### 6.1 为什么 Finding 要独立存在

一次会话可能同时出现推诿、解释错误和态度问题。每个问题有不同规则、严重程度和证据，因此必须分别表示。

### 6.2 为什么会话证据至少一条

Finding 是质检结论，必须有原话依据。没有会话证据时，结论无法回溯，也无法交给后续程序验证。

### 6.3 为什么需要 `claim`

有些问题只靠会话语义就能判断，例如明显推诿。

另一些需要核验事实，例如“是否符合退货条件”。`claim` 用来保存需要核验的那句具体说法。

### 6.4 为什么 `required_evidence` 使用固定选项

后续流程需要根据证据需求决定是否查询订单或业务知识。固定选项能避免自由字符串造成不一致，例如同时出现 `order`、`order_context`、`order_info`。

### 6.5 为什么外部证据默认空

Finding 刚由模型产生时，外部证据通常还没有获取。先允许空列表，后续工具和知识检索再把结果补充进来。

### 6.6 为什么 Schema 不验证证据真实性

Schema 只检查数据形状和字段关系。原话是否真实存在、订单编号是否匹配、知识片段是否来自本次检索，需要后续确定性校验。

这样职责清晰，也能让 Schema 保持简单。

## 7. 业务场景问题及回答

### 7.1 如果一条纯语义 Finding 没有外部证据怎么办？

不需要外部证据时，`required_evidence=[]`、`requires_external_verification=False`，外部证据也保持空列表。它会走直接判断路径。

### 7.2 如果 Finding 说需要外部验证，但没写需要什么证据怎么办？

应拒绝。当前校验要求外部验证标记和所需证据列表一致，否则后续无法决定查订单还是查知识。

### 7.3 如果 Finding 有一条会话原话，但原话并不存在怎么办？

T004 不会发现，因为 Schema 只负责保存 `message_id` 和 `quote`。后续验证任务才会检查消息是否存在、原话是否真的在消息中。

### 7.4 如果同一个问题同时需要订单和业务知识怎么办？

`required_evidence` 同时放两个固定选项；后续拿到两类证据后，再进入复判和证据校验。

### 7.5 如果出现新的证据来源怎么办？

先确认新来源是否有独立业务含义。不能直接把新字段塞进订单证据或知识证据。应扩展证据类型、所需证据选项、测试和后续处理规则。

### 7.6 如果外部证据查询失败怎么办？

T004 只定义外部证据可以为空，不决定失败流程。失败处理属于后续流程任务。

### 7.7 如果 Finding 没有会话证据怎么办？

拒绝。**没有原始会话依据的质检结论无法追溯**，也不符合项目可审计要求。

### 7.8 如果 `claim` 为空，但需要外部验证怎么办？

当前 T004 只校验“是否需要外部验证”和“需要哪些证据”的一致性，没有强制要求填写 Claim。是否需要增加这条规则，应根据后续模型输出和复判流程确认，不能在本任务中擅自扩展。

## 8. 面试问题与回答

### 问题 1：一条客服质检结果应该包含什么？

**回答：**

我会包含规则编号、问题类型、严重程度、原因、会话证据、是否需要外部核验、待核验说法、所需证据以及已经获取的外部证据。这样结论既能解释，也能追踪和继续处理。

### 问题 2：为什么一个会话要支持多个 Finding？

**回答：**

同一段客服对话可能同时出现推诿、业务解释错误和流程问题。如果只输出一个总标签，规则、严重程度和证据都会混在一起，后续统计和复核也不准确。

### 问题 3：为什么要区分会话证据、订单证据和知识证据？

**回答：**

它们来源不同，校验方式也不同。会话证据要校验原文，订单证据要校验订单和字段，知识证据要校验文档片段和来源。分开表示更清晰，也方便后续分别处理。

### 问题 4：为什么不能只用一个字符串表示证据？

**回答：**

字符串无法表达证据来源、消息编号、订单编号和文档片段。结构化证据才能让程序验证结论是否真实，并保留完整追踪链。

### 问题 5：为什么需要 `required_evidence` 列表？

**回答：**

不同 Finding 需要不同外部事实。列表可以清楚表达不需要外部证据、只要订单、只要知识，或者两者都需要。用布尔值只能说明“需要外部信息”，无法说明具体要什么。

### 问题 6：为什么不把路由逻辑写进 Finding Schema？

**回答：**

Schema 负责描述数据，流程负责决定怎么处理。`required_evidence` 表达需求，后续流程再决定调用哪个工具。把调用逻辑写进 Schema 会导致数据结构和执行逻辑耦合。

### 问题 7：为什么要检查 `requires_external_verification` 和 `required_evidence` 一致？

**回答：**

如果标记说需要外部验证，却没有说明需要什么证据，后续流程无法执行；如果标记说不需要，却填写了证据要求，也说明模型输出矛盾。入口直接拒绝能避免错误进入后续链路。

### 问题 8：为什么外部证据初始可以为空？

**回答：**

Finding 通常是质检模型先产生的，外部证据要等后续查询订单或知识检索后才有。初始为空是正常状态，可以区分“还没获取”和“数据结构错误”。

### 问题 9：如何支持后续增加新的证据类型？

**回答：**

先确认新证据是否有独立来源、独立校验方式和独立业务含义。满足条件后，再扩展固定证据类型、外部证据组合、测试和后续流程。不能为了未来可能出现的场景提前增加大量类型。

### 问题 10：Finding Schema 和证据校验的边界是什么？

**回答：**

Schema 检查字段类型、必要证据列表和外部验证标记是否一致；证据校验负责检查原话是否真实、订单是否匹配、知识片段是否来自本次检索。前者保证数据形状，后者保证事实可信。

## 9. 学习检查与答案

### 1. Finding 和 Conversation 是什么关系？

一条 Conversation 可以产生 0 条或多条 Finding。

### 2. Finding 和 Evidence 是什么关系？

Finding 是质检结论，Evidence 是支持这条结论的可追溯依据。

### 3. 为什么会话证据不能为空？

没有会话原话依据的质检结论无法追溯和验证。

### 4. 会话证据、订单证据和知识证据的用途分别是什么？

会话证据定位客服原话，订单证据保存结构化业务事实，知识证据保存业务文档片段。

### 5. 四种处理表达分别是什么？

不需要外部证据、需要订单、需要业务知识、同时需要订单和业务知识。

### 6. 为什么 `required_evidence` 和外部验证标记必须一致？

否则后续无法判断是否需要外部处理，也无法确定应该查询什么。

### 7. 为什么外部证据可以初始为空？

因为 Finding 产生时通常还没有执行外部查询，证据会在后续流程补充。

### 8. T004 是否验证原话真实存在？

不验证。T004 只定义和保存证据结构，原话真实性由后续验证任务处理。

### 9. 如果增加新的证据来源，应该先做什么？

先确认它是否有独立来源和校验方式，再决定扩展数据类型、固定选项、测试和后续流程。

### 10. 为什么不把调用订单工具的代码放进 Finding？

因为那属于后续流程执行，不属于数据契约。Schema 应保持只负责数据结构。

## 10. 一句话总结

Finding 是一次客服会话中的一条独立质检发现，Evidence 是支撑它的可追溯依据；T004 用结构化字段和固定选项表达结论、证据需求和四种后续情况，但不实现查询、复判或证据真实性校验。