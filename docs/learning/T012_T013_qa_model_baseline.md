# T012-T013 QA Model baseline：业务和设计学习笔记

## 1. 这组任务解决什么问题

T012-T013 负责把 Conversation 和 QARule 交给模型，并得到标准化 Finding。

链路：

```text
Conversation + enabled QARule
→ 构造 Prompt
→ 调用模型客户端
→ 读取 JSON
→ 校验 Finding Schema
→ 返回 list[Finding]
```

T013 定义通用模型接口，并在 `serving/local_qwen.py` 接入真实本地 Qwen 权重；单元测试使用 Fake Model Client，真实运行使用本地模型。

## 2. 为什么模型层要和 Agent 分开

```text
model/：让模型完成质检语义判断
agent/：根据 Finding 决定后续处理路径
```

模型负责：

- 理解客户和客服的多轮对话；
- 根据规则识别问题；
- 输出 Finding；
- 引用会话证据；
- 判断是否需要外部核验。

Agent 负责：

- 处理外部取证；
- 路由；
- 调用 Tool / RAG；
- 基于证据复判。

两者分开后，更换模型供应商不需要修改 Agent。

## 3. Prompt 设计

`build_qa_prompt()` 接收：

- `Conversation`
- `list[QARule]`

它只把 `enabled=True` 的规则放入 Prompt。

Prompt 要求模型：

1. 支持 0 条或多条 Finding；
2. 每条 Finding 引用 `message_id` 和原文；
3. 语义问题可不填 Claim；
4. 需要业务事实时填写 Claim 和 `required_evidence`；
5. `external_evidence` 初始为空；
6. 只输出 JSON，不输出 Markdown 或自由解释。

动态业务政策不写入 Prompt，而是通过后续 Tool / RAG 获取。

## 4. Structured Output

`QAModelOutput` 是模型输出的顶层结构：

```python
class QAModelOutput(BaseModel):
    findings: list[Finding]
```

它直接复用 `schemas.Finding`，所以模型输出和后续 Agent 使用同一个数据结构。

这样避免了：

- 模型层定义一套 Finding；
- Agent 层再定义另一套 Finding；
- 字段转换时出现丢失或不一致。

## 5. 模型客户端抽象

`ModelClient` 只要求：

```python
def generate(prompt: str) -> str
```

具体供应商可以是：

- vLLM；
- 本地 Transformers；
- OpenAI 兼容接口；
- 测试用 Fake Model Client。

因此 QA Model wrapper 不知道 HTTP、GPU 或具体服务细节。

## 6. 真实本地 Qwen 服务

本地权重路径：

```text
G:\LLM\modelscope\hub\models\qwen\Qwen3-VL-2B-Instruct
```

`LocalQwenClient`：

- 实现 `generate(prompt) -> str`；
- 首次调用时才加载模型，避免导入模块就占用显存；
- 使用 `AutoProcessor` 处理 Chat Template；
- 使用 `Qwen3VLForConditionalGeneration` 执行文本生成；
- 支持通过 `LOCAL_QWEN_MODEL_PATH` 覆盖默认路径。

真实模型运行时：

```python
client = LocalQwenClient()
qa_model = QAModel(client)
findings = qa_model.analyze(conversation, rules)
```

Fake Model Client 只用于单元测试，不代替真实服务。

本地 Qwen 可能把 JSON 包在：

```text
```json
{...}
```
```

因此 `parse_json_output()` 会先去掉 Markdown JSON 包装，再交给 Pydantic 校验。

真实 Case A 已经验证能够返回标准 Finding。Case B 当前基础模型可能返回 0 条 Finding，这不是服务接入失败，而是未微调模型在复杂业务规则召回上的能力不足，后续通过 SFT 和评测改进。
## 6. 错误处理

模型输出可能出现两类错误：

### 6.1 非法 JSON

例如：

```text
这是一个 Finding: ...
```

不是 JSON，无法解析。

处理：抛出 `InvalidModelOutput("model output is not valid JSON")`。

### 6.2 JSON 合法但 Schema 错误

例如缺少 `conversation_evidence`，或 `required_evidence` 使用了未知值。

处理：Pydantic 校验失败后，统一转换成 `InvalidModelOutput`。

这样上层只需要处理一种明确的模型输出异常。

## 7. 业务场景

### Case A：纯语义推诿

输出 Finding：

```text
risk_type = blame_shifting
requires_external_verification = false
required_evidence = []
```

不需要查询订单或知识。

### Case B：售后资格解释

输出 Finding：

```text
claim = 耳机购买十几天后是否可以退货
requires_external_verification = true
required_evidence = [order_context, business_knowledge]
```

后续 Agent 需要订单事实和业务知识。

### Case C：退款到账承诺

输出 Finding：

```text
claim = 今晚是否一定到账
requires_external_verification = true
required_evidence = [order_context]
```

后续需要查询订单退款状态。

## 8. 真实面试问题

### 问题 1：为什么 Prompt 不直接写入业务政策？

**回答：**

活动、退款和售后政策会变化。如果写进 Prompt，每次政策变化都要改 Prompt 甚至重新训练。动态知识应通过 RAG 或 Tool 查询，模型只负责提出 Claim 和证据需求。

### 问题 2：为什么要定义模型输出 Schema？

**回答：**

模型输出需要被 Agent 和 Evidence 校验程序稳定消费。Schema 可以把自然语言输出变成明确的 Finding 结构，并在数据不完整时尽早失败。

### 问题 3：为什么用模型客户端抽象？

**回答：**

模型供应商的 HTTP 协议和部署方式不同，但质检业务只关心 Prompt 到文本的接口。抽出 `generate()` 后，可以在测试中使用 Fake Client，在生产中替换 vLLM 或其他服务。

### 问题 4：为什么要区分“模型输出错误”和业务判断错误？

**回答：**

输出错误是模型没有遵守 JSON 或 Finding Schema；业务判断错误是 Schema 正确但结论不准。前者需要格式重试或异常处理，后者需要评测、反馈和模型优化。

## 9. 学习检查与答案

### 1. T012 的输入是什么？

Conversation 和启用规则的列表。

### 2. T012 的输出是什么？

符合 Finding Schema 的结构化结果。

### 3. 为什么外部证据初始为空？

模型只负责发现问题和提出证据需求，真实订单和知识证据要由后续 Tool/RAG 获取。

### 4. Fake Model Client 的作用是什么？

在不连接真实模型服务的情况下，稳定测试 Prompt 解析、JSON 转换和异常分支。

### 5. 模型层和 Agent 层的边界是什么？

模型层负责生成 Finding，Agent 层负责根据 Finding 路由、取证和复判。

## 10. 一句话总结

T012 把会话和规则变成受约束的质检 Prompt，T013 通过通用模型客户端得到 JSON，再校验成统一 Finding；模型只输出质检判断和证据需求，不负责外部查证。