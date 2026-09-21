# T023-T026 分层评测与最终验收：业务和设计学习笔记

## 1. 这组任务做什么

T023-T026 分别评估模型、RAG、Agent/Evidence 和服务性能，并汇总最终验收结果。

```text
QA Model
→ RAG
→ Agent / Evidence
→ Serving
→ 最终报告
```

核心原则：

- 分层评测；
- 不伪造指标；
- 明确小样本和冒烟实验边界；
- 已完成能力与设计规划分开记录。

## 2. T023：QA Model 评测

### 2.1 Finding 分类 F1

用于衡量模型识别的问题类别是否正确。

标签示例：

```text
rule-blame|blame_shifting
rule-after-sale|policy_explanation_error
```

F1 同时考虑：

- 预测错误类别；
- 漏掉正确类别。

### 2.2 External Verification Trigger F1

衡量模型是否正确决定是否需要外部事实核验。

例如：

```text
Case A 推诿：不需要外部核验
Case B 售后：需要订单 + 知识
Case C 退款承诺：需要订单
```

### 2.3 Evidence 定位准确率

检查 Finding 引用的 `message_id` 和 quote 是否对应预期证据。

### 2.4 Schema 成功率

判断模型输出能否通过 Finding Schema。

### 2.5 Base vs SFT

Base Qwen 和 SFT adapter 必须在：

- 同一测试集；
- 同一 Prompt；
- 同一推理参数；

下比较。

当前结果：

```text
Base F1 = 0.5
SFT（1-step）F1 = 0.5
```

1-step adapter 只验证训练流程，不能证明模型提升。

## 3. T024：RAG 评测

### 3.1 Recall@K

在 TopK 召回片段中是否包含正确 source。

### 3.2 Rerank Top1/Top3

经过 CrossEncoder 重排后，正确 source 是否排在第一名或前三名。

### 3.3 过期政策泄漏率

检查已经失效的政策是否会被错误召回。

当前结果：

```text
Recall@K = 1.0
Rerank Top1 = 1.0
Rerank Top3 = 1.0
过期政策泄漏率 = 0.0
```

评测集只有 5 条 query，不能代表企业生产规模。

## 4. T025：Agent 与 Evidence 评测

### 4.1 Routing Accuracy

检查 direct、order、knowledge、combined 等路径是否正确。

### 4.2 Tool Argument Accuracy

检查传入 Tool 的订单 ID 等参数是否正确。

### 4.3 Evidence Validation Accuracy

检查 Conversation Evidence 的存在性、角色和原文是否通过。

### 4.4 Unsupported Claim Rate

统计需要外部核验但没有 Claim 的比例。

### 4.5 代表 Case

推诿、售后、退款三类 Case 应能跑通对应路径。

当前结果：

```text
Routing Accuracy = 1.0
Tool Argument Accuracy = 1.0
Evidence Validation Accuracy = 1.0
Unsupported Claim Rate = 0.0
代表 Case 通过率 = 1.0
```

这是确定性小样本结果，不代表所有线上数据。

## 5. T026：Serving Benchmark

当前测量本地 Qwen3-VL-2B-Instruct：

```text
requests = 2
latency = 1.5548 秒/请求
串行吞吐 = 0.6432 请求/秒
GPU memory = 4121.96 MB
```

注意：

- 这是单进程串行测试；
- 不是并发吞吐；
- 真实 vLLM 服务没有启动；
- 量化模型没有参与 benchmark。

## 6. 为什么分层评测

如果把所有指标混成一个分数，无法知道问题来自：

- 模型识别；
- RAG 召回；
- Agent 路由；
- Tool 调用；
- 证据校验；
- 服务性能。

分层后可以定位瓶颈，并分别优化。

## 7. 真实面试问题

### 问题 1：为什么模型、RAG 和 Agent 要分开评测？

**回答：**

它们负责不同环节。模型影响 Finding 识别，RAG 影响知识召回，Agent/Tool 影响证据获取与路由。分开评测可以定位错误来源，避免把所有问题都归因于模型。

### 问题 2：Why Base vs SFT 要使用同一测试集？

**回答：**

只有输入、Prompt 和推理参数一致，指标差异才能归因于模型参数变化。如果测试集不同，无法判断提升来自训练还是样本变化。

### 问题 3：为什么 F1 不能单独说明系统可用？

**回答：**

F1 只反映分类效果。系统还需要 Schema 成功率、Evidence 准确率、Tool 参数正确率和服务时延。一个分类 F1 很高的模型仍可能无法稳定输出结构化结果。

### 问题 4：为什么 1-step 训练结果不能作为正式结论？

**回答：**

1-step 只验证数据加载、LoRA、Trainer 和保存流程是否可运行。它没有足够训练信号，不能用于声称模型准确率提升。

### 问题 5：Serving benchmark 为什么区分 latency 和 throughput？

**回答：**

latency 是单个请求耗时，throughput 是单位时间完成多少请求。当前测试是串行请求，因此只能得到串行吞吐，不能冒充高并发吞吐。

## 8. 学习检查与答案

### 1. Recall@K 评估什么？

正确来源是否出现在 TopK 召回结果中。

### 2. Rerank Top1 评估什么？

正确来源是否被重排到第一名。

### 3. Routing Accuracy 评估什么？

Finding 是否被送到正确处理路径。

### 4. Schema 成功率为什么重要？

模型即使语义判断正确，如果结构不合法，后续 Agent 也无法稳定消费。

### 5. 为什么当前结果不能代表生产效果？

测试集小、SFT 只有 1-step、真实企业数据和真实 vLLM 部署尚未接入。

## 9. 一句话总结

T023-T026 通过模型、RAG、Agent/Evidence 和 Serving 四层评测验证了算法闭环；RAG 和确定性 Agent 指标表现良好，1-step SFT 仅完成流程冒烟，必须经过正式训练和更大规模测试集后才能宣称效果提升。