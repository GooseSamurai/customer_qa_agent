# 评测与验收报告

## 1. 评测范围

本报告记录当前仓库真实可运行的评测结果，不包含虚构的生产指标。

```text
Model evaluation：Base Qwen vs 1-step LoRA adapter
RAG evaluation：BGE Embedding + Chroma + BGE Reranker
Agent evaluation：Router、Tool argument、Evidence validation
Serving benchmark：本地 Qwen 串行延迟、吞吐和显存
```

## 2. Model Evaluation

测试集：

```text
3 条代表 Case：推诿、售后资格、退款到账承诺
```

Base Qwen：

```text
finding_classification_f1 = 0.5
external_verification_trigger_f1 = 0.0
evidence_localization_accuracy = 0.0
schema_success_rate = 1.0
```

1-step LoRA adapter：

```text
finding_classification_f1 = 0.5
external_verification_trigger_f1 = 0.0
evidence_localization_accuracy = 0.0
schema_success_rate = 0.3333
```

结论：

- Base 和 SFT 使用相同测试集、相同提示和相同推理设置；
- 1-step adapter 只用于验证训练链路，不能视为有效微调；
- 当前结果不能证明 SFT 已提升质检准确率；
- 正式训练需要使用经过清洗的历史复核数据并重新评测。

## 3. RAG Evaluation

测试集：

```text
5 条 query → expected source 标注
```

结果：

```text
recall_at_k = 1.0
rerank_top1 = 1.0
rerank_top3 = 1.0
num_cases = 5
expired_policy_leak_rate = 0.0
```

结论：

- 当前六份拟真业务文档的全部标注 query 都能召回正确 source；
- BGE Reranker 将正确 source 排在 Top1；
- 过期政策在 `as_of` 过滤后未进入结果；
- 评测集较小，不能代表生产规模效果。

## 4. Agent and Evidence Evaluation

结果：

```text
routing_accuracy = 1.0
tool_argument_accuracy = 1.0
evidence_validation_accuracy = 1.0
unsupported_claim_rate = 0.0
representative_case_pass_rate = 1.0
num_routing_cases = 4
```

结论：

- direct、order、knowledge、combined 路由通过确定性测试；
- Order Tool 返回的 order_id 与查询参数一致；
- Conversation Evidence 的存在性、角色和原文检查通过；
- 当前代表 Case 数量少，仍需要扩充评测数据。

## 5. Serving Benchmark

本地 Qwen3-VL-2B-Instruct，单进程串行调用：

```text
requests = 2
elapsed_seconds = 3.1095
latency_seconds_per_request = 1.5548
serial_requests_per_second = 0.6432
gpu_memory_mb = 4121.96
```

结论：

- 记录了真实 latency、串行吞吐和 GPU 显存峰值；
- 这不是高并发吞吐测试；
- 真实 vLLM 服务尚未启动，因此没有 vLLM 版本对比；
- 量化部署和大 batch 性能尚未实现。

## 6. 当前完成与未完成

已完成：

- Schema、RAG、本地 Qwen、Agent Workflow；
- SFT 数据构建和 LoRA 训练入口；
- 1-step 真实 LoRA 冒烟训练和 adapter 保存；
- SQLite、FastAPI、Review export；
- vLLM HTTP 客户端和服务适配；
- Model、RAG、Agent、Evidence、Serving 评测脚本。

未完成：

- 正式规模 LoRA-SFT 和准确率提升验证；
- 真实 vLLM 服务部署；
- 量化推理；
- 多并发 Serving benchmark；
- 企业真实文档和真实人工复核数据接入。

## 7. 复现命令

```powershell
python -m pytest
python -m evaluation.rag_eval
python -m evaluation.serving_benchmark
```

模型评测需要先生成 SFT adapter，然后分别用 Base 和 adapter 运行 `evaluation.model_eval`。Agent 评测通过 `evaluation.agent_eval.evaluate_agent()` 执行。