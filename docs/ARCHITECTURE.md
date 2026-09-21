# ARCHITECTURE.md

## 1. 总体架构

```text
Enterprise normalized Conversation + QA Rules
                    ↓
                QA Model
                    ↓
               0..N Findings
                    ↓
          Finding / Claim Router
          /         |          \
     direct    Order Context   Business Knowledge RAG
          \         |          /
               Evidence Pack
                    ↓
          Grounded Re-evaluation
                    ↓
          Evidence Verification
                    ↓
               Final Findings
                    ↓
             Review / Feedback
                    ↓
             SFT candidate data

QA Model runtime → serving/vLLM
```

## 2. 公共领域对象

### 2.1 Conversation

统一客服会话。作为在线质检和离线训练的基础输入对象。

建议字段：

```text
conversation_id
channel
customer_id
agent_id
order_ids
start_time
messages[]
```

`Message`：

```text
message_id
role
 timestamp
text
```

### 2.2 QARule

表示当前企业启用的一条质检规则。

```text
rule_id
name
dimension
description
positive_condition
exclude_condition
severity
need_external_fact
enabled
version
```

### 2.3 Finding

系统最重要的质检结果单位。一条会话可以有多个 Finding。

建议字段：

```text
finding_id（持久化后）
rule_id
risk_type
severity
reason
conversation_evidence
claim
requires_external_verification
required_evidence
confidence
external_evidence[]
status
```

### 2.4 Evidence

统一表达可追溯证据。

最少三类：
- `ConversationEvidence`：message_id + quote；
- `OrderEvidence`：order_id + field/value + queried_at；
- `KnowledgeEvidence`：source_id + chunk_id + text + metadata。

## 3. 模块职责与依赖

| 目录 | 只负责什么 | 可以依赖 | 不应该做什么 |
|---|---|---|---|
| `schemas/` | 共享 Pydantic 数据契约 | Pydantic/stdlib | 调模型、查库、路由 |
| `model/` | Prompt、QA 模型抽象、Structured Output、结果 Normalize | schemas、serving client interface | Tool/RAG 编排 |
| `agent/` | State、Router、Workflow、Grounded Judge | schemas、model、tools、evidence | 自己实现数据库/RAG 底层 |
| `tools/` | 企业业务能力的受控适配器 | schemas、rag、db/HTTP client | 决定调用哪个 Tool |
| `rag/` | 文档 ingestion、metadata filter、向量召回、rerank | schemas、vector/embedding client | 生成质检结论 |
| `evidence/` | 确定性证据校验 | schemas | 自由 Agent 推理 |
| `training/` | SFT 数据构造、LoRA 训练入口 | schemas、离线数据 | 在线 Agent |
| `feedback/` | Review → SFT 候选样本 | db、schemas | 自动训练 |
| `serving/` | vLLM/runtime 接入 | model runtime contract | 业务路由 |
| `api/` | HTTP 请求/响应和服务入口 | schemas、application service/agent | 核心算法实现 |
| `db/` | 持久化、Repository | schemas | Agent 决策 |
| `evaluation/` | 离线评测与 Benchmark | 各模块公开接口 | 修改线上行为 |
| `tests/` | 单元/契约/集成测试 | 所有公开接口 | 业务实现 |

## 4. 依赖方向

```text
schemas
  ↓
model   db   rag   evidence
               ↓
             tools
               ↓
             agent
               ↓
              api

serving → model runtime contract
feedback → db + schemas
training → schemas + exported data
evaluation/tests → public interfaces
```

禁止循环依赖。

## 5. 在线主流程

### 5.1 输入校验

`api/` 将 JSON 转换为 `Conversation` 和 Rule 上下文。无效请求在进入模型前失败。

### 5.2 QA Model

`model/qa_model.py` 接收：

```text
Conversation
+ enabled QARules
```

输出标准 `list[Finding]`。

模型可以通过 Prompt Baseline 或后续 LoRA-SFT 模型实现，但上层不应依赖具体模型供应商。

### 5.3 Router

`agent/router.py` 对单个 Finding 路由。

典型结果：

```text
direct
order_context
business_knowledge
order_and_knowledge
human_review
```

Router 不直接执行 Tool。

### 5.4 Tools

`tools/order_context.py`：查询订单、物流、退款、售后、优惠等结构化上下文。

`tools/knowledge_tool.py`：调用 `rag/`，查询动态业务规则和文档知识。

### 5.5 Grounded Judge

`agent/grounded_judge.py` 接收：

```text
原 Finding/Claim
+ Conversation Evidence
+ External Evidence
```

输出修正/确认后的 Finding，不重新进行无限制 Agent 规划。

### 5.6 Evidence Verification

`evidence/verifier.py` 负责程序可确定的问题：
- quote 是否存在；
- message role 是否正确；
- order/source id 是否匹配；
- knowledge evidence 是否来自本次检索；
- 明确有效期是否满足；
- required evidence 是否齐全。

语义判断留给 QA Model / Grounded Judge，确定性事实校验留给 verifier。

## 6. RAG 架构

### ingestion

`rag/ingest.py`：
- 解析企业业务文档；
- 按自然规则结构切分；
- 写入 source/chunk metadata；
- 生成向量并入库。

### retrieval

`rag/retrieve.py`：

```text
Claim / query
→ metadata filter
→ vector recall TopK
→ candidate chunks
```

关键 Metadata：

```text
business_scene
channel
category
policy_type
effective_date
expire_date
priority
```

### rerank

`rag/rerank.py` 对候选 chunk 重新排序，并保留 source trace。

## 7. 训练架构

`training/build_sft_data.py`：把已确认的 Conversation + Rules + 人工 Finding 构造成统一 SFT 格式。

`training/train_lora.py`：负责 LoRA-SFT 训练入口；具体模型、参数和框架通过配置传入，不硬编码成架构事实。

SFT 学：
- 质检标签和边界；
- 多 Finding；
- Evidence 定位；
- Claim 抽取；
- 外部核验触发；
- Structured Output。

SFT 不承担频繁变化的活动/价格/售后政策记忆。

## 8. Feedback 架构

人工 Review：

```text
confirmed
false_positive
correction
```

`feedback/export_sft.py` 只负责将合格复核结果转成 SFT 候选，不自动启动训练。

## 9. Serving 架构

`serving/vllm_client.py` 封装模型推理调用。

`serving/service.py` 暴露稳定模型服务接口给 `model/` 使用。

业务 Agent 不应依赖 vLLM 的具体 HTTP 参数，从而允许测试时替换为 Fake Model Client。

## 10. DB 最小边界

建议持久化对象：

```text
qa_rules
qa_cases
qa_findings
qa_reviews
agent_runs
finding_evidence（可选）
```

数据库只是持久化，不决定业务路由。

## 11. 测试分层

```text
Unit tests
  schemas / router / verifier / retriever / tool adapters

Contract tests
  model output schema / tool response schema / API schema

Integration tests
  Conversation → Finding → Agent → Tool/RAG → Evidence → Result

Evaluation
  model / RAG / Agent / serving metrics
```
