# T022 vLLM Serving：业务和设计学习笔记

## 1. T022 解决什么问题

LoRA 训练完成后，模型不应该直接嵌在业务代码里运行。

T022 把模型推理放到独立 vLLM 服务后面：

```text
QA Model
→ ModelClient.generate(prompt)
→ VLLMService
→ VLLMClient
→ vLLM OpenAI 兼容接口
```

业务 Agent 不需要知道：

- vLLM 的 URL；
- HTTP 请求格式；
- timeout；
- 服务异常实现。

## 2. 为什么使用 vLLM

vLLM 适合部署微调后的 Qwen 模型，并对外提供 OpenAI 兼容接口。

优点：

- 与业务 Agent 解耦；
- 可以独立部署和扩容；
- 模型更新不需要修改 Agent；
- 支持多个业务调用方复用同一个模型服务。

当前项目只实现客户端和服务适配层，不要求本地常驻真实 GPU 服务，测试使用 Mock HTTP。

## 3. VLLMClient

### 3.1 输入

```python
client = VLLMClient(
    base_url="http://localhost:8000",
    model_name="qwen-adapter",
    timeout=60,
    max_tokens=1024,
)
```

### 3.2 输出

```python
client.generate(prompt)
```

返回模型生成的文本。

内部调用：

```text
POST /v1/chat/completions
```

请求中包含：

- model；
- messages；
- temperature=0；
- max_tokens。

### 3.3 异常

```text
请求超时 → VLLMServiceError("vLLM request timed out")
HTTP错误 / 响应结构错误 → VLLMServiceError("vLLM returned an invalid response")
```

上层业务不需要分别处理 httpx 异常。

## 4. VLLMService

`VLLMService` 是业务层和 HTTP 客户端之间的适配器。

```python
service = VLLMService(client)
qa_model = service.create_qa_model()
```

它让 `QAModel` 继续使用统一的：

```python
generate(prompt) -> str
```

当模型从本地 Transformers 切换到 vLLM 时，QA Model 和 Agent 不需要改动。

## 5. 本地 Qwen 与 vLLM 的区别

```text
LocalQwenClient
    直接加载本地权重
    适合开发、训练前后验证
    启动慢，占用本机显存

VLLMClient
    只调用远程 HTTP 服务
    适合部署和业务调用
    不关心模型怎么加载
```

两者实现同一个 `generate()` 契约，因此可以互换。

## 6. 业务场景

### 场景 1：本地开发

使用 `LocalQwenClient` 直接加载 Qwen，快速验证 Prompt 和 finding。

### 场景 2：服务化部署

启动 vLLM 服务后，配置 `VLLMClient` 的 base_url 和 model_name。

QA Model 和 Agent 不需要修改。

### 场景 3：模型服务超时

客户端转换为统一的 `VLLMServiceError`，API 可以将其映射成明确的服务异常。

### 场景 4：响应格式异常

如果 vLLM 返回缺少 `choices` 的响应，客户端直接报错，不把非法内容交给 Finding Schema 解析。

### 场景 5：本地没有 GPU 服务

测试使用 Mock HTTP，不需要启动 vLLM 和占用 GPU。

## 7. 真实面试问题

### 问题 1：为什么不直接在 Agent 里调用模型？

**回答：**

Agent 关心质检和证据路由，不应该依赖 HTTP 参数、模型地址和服务异常。通过 ModelClient 接口隔离后，本地模型、vLLM 或其他服务可以互换。

### 问题 2：为什么 vLLM 客户端不用安装 vllm 包？

**回答：**

客户端只访问 OpenAI 兼容 HTTP 接口，不负责启动和加载模型。vLLM 运行在独立服务进程中，业务侧只需要 HTTP 客户端。

### 问题 3：为什么要区分 timeout 和服务错误？

**回答：**

timeout 表示请求在限定时间内没有完成，服务错误可能来自 HTTP 状态、响应结构或服务不可用。统一成业务异常后，API 可以稳定处理，而不是向业务层泄漏底层库异常。

### 问题 4：模型换成 SFT adapter 后客户端要改吗？

**回答：**

只需要修改 vLLM 服务加载的模型或 adapter 名称，客户端调用协议不变，Agent 和 QA Model 不需要变化。

## 8. 学习检查与答案

### 1. VLLMClient 的核心接口是什么？

`generate(prompt) -> str`。

### 2. 请求发送到哪个接口？

`/v1/chat/completions`。

### 3. 超时如何表示？

抛出统一的 `VLLMServiceError`。

### 4. VLLMService 的作用是什么？

把 vLLM 客户端适配为 QA Model 可使用的模型客户端。

### 5. 为什么业务层不应感知 HTTP 细节？

因为 HTTP 细节属于部署适配，不是质检业务逻辑。隔离后可以替换服务、测试和部署环境。

### 6. 当前测试需要真实 GPU 吗？

不需要，使用 Mock HTTP 验证契约。

## 9. 一句话总结

T022 用 VLLMClient 封装 vLLM HTTP 细节，用 VLLMService 适配 QA Model，使本地 Qwen、SFT adapter 和远程 vLLM 可以共用同一套业务调用接口。