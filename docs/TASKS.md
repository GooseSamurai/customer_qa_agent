# TASKS.md

## 使用规则

- Codex 一次只实现一个 Task。
- 一个 Task 尽量控制在 1~3 个核心实现文件和对应测试。
- 完成前必须满足 Acceptance。
- 未完成前不要提前实现后续 Task。
- `Status` 只允许：`TODO / IN_PROGRESS / DONE / BLOCKED`。

---

# Milestone M1：仓库与核心数据契约

## T001 Repository skeleton and Python project setup

**Status:** DONE  
**Depends on:** None

**Target:**
- 创建约定目录和必要的 `__init__.py`；
- 建立最小 Python 项目配置；
- 配置 pytest；
- 不实现任何业务逻辑。

**Acceptance:**
- `pytest` 可以执行；
- 所有业务目录可以正常 import；
- 没有加入当前阶段不需要的大型依赖；
- README 中的目录与真实仓库一致。

**Learning:** Python package、module、import、pytest 基础。

---

## T002 Conversation Schema

**Status:** DONE  
**Depends on:** T001

**Target files:**
- `schemas/conversation.py`
- `tests/schemas/test_conversation.py`

**Acceptance:**
- 定义 `Message` 与 `Conversation`；
- role 有明确约束；
- messages 不能为空；
- 同一 Conversation 中 message_id 不重复；
- 正常/异常输入均有测试。

**Learning:** Pydantic、嵌套模型、字段校验、自定义 validator。

---

## T003 QA Rule Schema

**Status:** DONE  
**Depends on:** T001

**Target files:**
- `schemas/qa_rule.py`
- `tests/schemas/test_qa_rule.py`

**Acceptance:**
- 覆盖 rule_id、dimension、severity、description、conditions、enabled、version 等核心字段；
- severity / enabled 等字段有清晰类型；
- Rule 不包含数据库或 Prompt 逻辑。

**Learning:** 配置对象与业务逻辑解耦。

---

## T004 Finding and Evidence Schema

**Status:** DONE
**Depends on:** T002, T003

**Target files:**
- `schemas/finding.py`
- `schemas/evidence.py`
- `tests/schemas/test_finding.py`

**Acceptance:**
- 定义 Finding；
- 定义 ConversationEvidence / OrderEvidence / KnowledgeEvidence；
- Finding 支持 `requires_external_verification`、`claim`、`required_evidence`；
- Schema 能表达 direct / order / knowledge / order+knowledge 情况；
- 不实现 Router。

**Learning:** Union/Enum、领域模型设计、为什么 Finding 是系统核心契约。

---

## T005 Mock fixtures and representative cases

**Status:** DONE  
**Depends on:** T002, T003, T004

**Target:**
- `tests/fixtures/` 或等价目录；
- 建立 Case A/B/C；
- 建立少量 Mock Rules / Order Context / Knowledge documents。

**Acceptance:**
- 推诿、售后资格、退款承诺三个代表 Case 可被测试复用；
- Mock 数据只模拟企业输入，不写业务判断逻辑。

**Learning:** fixture、测试数据与生产逻辑分离。

---

# Milestone M2：Evidence 与外部能力

## T006 Conversation Evidence Verifier

**Status:** DONE  
**Depends on:** T004, T005

**Target files:**
- `evidence/verifier.py`
- `tests/evidence/test_verifier.py`

**Acceptance:**
- 能验证 message_id 是否存在；
- quote 是否存在于指定 agent message；
- 不允许引用 customer 消息作为客服违规原话；
- 返回明确验证结果/错误原因。

**Learning:** 确定性验证为什么优于二次 LLM。

---

## T007 Order Context Tool contract and Mock implementation

**Status:** DONE  
**Depends on:** T004, T005

**Target files:**
- `tools/order_context.py`
- `tests/tools/test_order_context.py`

**Acceptance:**
- 定义稳定 Tool 输入/输出；
- Mock 实现支持订单、物流、退款、售后、优惠等最小上下文字段；
- order 不存在时返回明确错误，不伪造值；
- Tool 不做路由和最终质检判断。

**Learning:** Tool 本质、接口封装、Mock API。

---

## T008 Business Knowledge document schema and ingestion

**Status:** DONE  
**Depends on:** T001, T005

**Target files:**
- `rag/ingest.py`
- 对应 tests

**Acceptance:**
- 定义 source/chunk 和 Metadata；
- 支持 channel/category/policy_type/effective_date/expire_date 等字段；
- 用最小样本文档完成结构化切分；
- 暂不实现复杂向量库。

**Learning:** Chunk 与 Metadata 的业务意义。

---

## T009 Basic Retriever

**Status:** DONE  
**Depends on:** T008

**Target files:**
- `rag/retrieve.py`
- 对应 tests

**Acceptance:**
- 支持 Metadata Filter；
- 支持 embedding/vector TopK recall；
- 返回保留 source_id/chunk_id 的候选结果；
- 能在新旧政策样例中排除明显过期文档。

**Learning:** Embedding、TopK、Metadata Filter。

---

## T010 Reranker

**Status:** DONE  
**Depends on:** T009

**Target files:**
- `rag/rerank.py`
- 对应 tests

**Acceptance:**
- 对 Retriever 候选进行二次相关性排序；
- 结果保留原 Evidence trace；
- Reranker 可替换/Mock，测试不依赖真实在线模型。

**Learning:** Bi-Encoder recall vs Cross-Encoder rerank。

---

## T011 Business Knowledge Tool

**Status:** DONE  
**Depends on:** T009, T010

**Target files:**
- `tools/knowledge_tool.py`
- 对应 tests

**Acceptance:**
- 将 RAG 封装成稳定 Tool；
- 输入 Claim/query + filters；
- 输出 KnowledgeEvidence；
- Tool 不决定是否应该被调用。

**Learning:** RAG 与 Agent Tool 的边界。

---

# Milestone M3：QA Model baseline

## T012 Prompt and structured output baseline

**Status:** TODO  
**Depends on:** T003, T004, T005

**Target files:**
- `model/prompt.py`
- `model/output_schema.py`
- 对应 tests

**Acceptance:**
- Prompt 能接收 Conversation + enabled Rules；
- 明确多 Finding、Evidence、Claim、required_evidence 输出要求；
- output schema 与 `schemas/Finding` 一致；
- 本任务不接真实模型服务。

**Learning:** Prompt contract、Structured Output、为什么 Prompt 不保存动态政策。

---

## T013 QA Model wrapper

**Status:** TODO  
**Depends on:** T012

**Target files:**
- `model/qa_model.py`
- 对应 tests

**Acceptance:**
- 定义与具体供应商解耦的模型调用接口；
- 输入 Conversation + Rules；
- 输出标准 Findings；
- 支持 Fake Model Client 测试；
- 错误 JSON/Schema 有明确异常处理。

**Learning:** 模型 API 封装、依赖注入、Normalize。

---

# Milestone M4：Agent 工作流

## T014 Claim Router

**Status:** TODO  
**Depends on:** T004, T007, T011

**Target files:**
- `agent/router.py`
- 对应 tests

**Acceptance:**
- Router 输入单个 Finding；
- 输出 direct/order_context/business_knowledge/order_and_knowledge/human_review；
- Router 不直接调用 Tool；
- 未知 required_evidence 不猜测。

**Learning:** 条件路由、Finding 粒度 Agent。

---

## T015 Grounded Judge

**Status:** TODO  
**Depends on:** T013, T014

**Target files:**
- `agent/grounded_judge.py`
- 对应 tests

**Acceptance:**
- 输入原 Finding + 已获取 Evidence；
- 输出确认/修正后的 Finding；
- 只围绕原 Claim 与 Evidence 复判；
- 支持 Fake Model Client。

**Learning:** Grounding、为何 Tool 返回不等于最终结论。

---

## T016 Agent State and workflow

**Status:** TODO  
**Depends on:** T006, T007, T011, T014, T015

**Target files:**
- `agent/state.py`
- `agent/workflow.py`
- 对应 tests

**Acceptance:**
- State 只保留节点间需要共享的数据；
- 串起 direct / order / knowledge / combined / human paths；
- Tool failure 和 Evidence failure 有明确路径；
- workflow 可用代表 Case 做集成测试。

**Learning:** LangGraph State、Node、conditional edge、异常分支。

---

# Milestone M5：API、持久化与人工反馈

## T017 Minimal persistence layer

**Status:** TODO  
**Depends on:** T004, T016

**Target:**
- `db/` repository + minimal models
- tests

**Acceptance:**
- 能保存 case、findings、evidence、review、agent run 的最小信息；
- DB 层不包含 Router/LLM 逻辑；
- 测试环境可使用 SQLite。

**Learning:** Repository pattern、持久化边界。

---

## T018 Quality analysis API

**Status:** TODO  
**Depends on:** T016, T017

**Target:**
- `api/` minimal endpoint
- tests

**Acceptance:**
- 接收 Conversation；
- 调用应用/workflow；
- 返回标准质检结果；
- API 不直接写 RAG/Tool/LLM 业务逻辑。

**Learning:** FastAPI、Pydantic request/response、service separation。

---

## T019 Review and feedback export

**Status:** TODO  
**Depends on:** T017

**Target files:**
- `feedback/export_sft.py`
- review endpoint/repository changes as needed
- tests

**Acceptance:**
- 支持 confirmed / false_positive / correction；
- 能从合格 review 生成 SFT candidate；
- 不自动启动训练。

**Learning:** Human-in-the-loop 与训练数据闭环。

---

# Milestone M6：SFT 与 Serving

## T020 SFT dataset builder

**Status:** TODO  
**Depends on:** T004, T019

**Target files:**
- `training/build_sft_data.py`
- tests

**Acceptance:**
- 将 Conversation + Rules + 人工确认 Finding 转成统一训练格式；
- 区分 train/valid/test；
- 不把动态政策答案硬编码为训练目标；
- 输出可检查的数据统计。

**Learning:** Instruction/SFT 数据组织、数据泄漏边界。

---

## T021 LoRA training entrypoint

**Status:** TODO  
**Depends on:** T020

**Target files:**
- `training/train_lora.py`
- config files as needed

**Acceptance:**
- 能通过配置指定 base model、LoRA 参数、数据路径；
- 训练/验证配置分离；
- 保存 adapter 和训练日志；
- 参数以实际实验为准，不把建议值写死为项目结果。

**Learning:** LoRA、Chat Template、训练验证流程、排障。

---

## T022 vLLM serving client and service

**Status:** TODO  
**Depends on:** T013, T021

**Target files:**
- `serving/vllm_client.py`
- `serving/service.py`
- tests with mocked HTTP

**Acceptance:**
- QA Model 可通过统一 client 调用 vLLM；
- 业务 Agent 不感知 vLLM HTTP 细节；
- timeout / service error 有明确异常；
- 测试不要求真实 GPU 服务常驻。

**Learning:** vLLM 服务化、模型服务与业务服务解耦。

---

# Milestone M7：评测与验收

## T023 Model evaluation

**Status:** TODO  
**Depends on:** T013, T021

**Acceptance:**
- 至少统计 Finding 分类 F1、External Verification Trigger F1、Evidence 定位准确率、JSON/Schema 成功率；
- Base vs SFT 使用同一测试集和推理设置。

---

## T024 RAG evaluation

**Status:** TODO  
**Depends on:** T009, T010

**Acceptance:**
- 构造 query/claim → relevant source 标注；
- 统计 Recall@K、rerank Top1/Top3；
- 单独观察旧政策/错误版本召回。

---

## T025 Agent and evidence evaluation

**Status:** TODO  
**Depends on:** T016

**Acceptance:**
- Routing Accuracy；
- Tool Argument Accuracy；
- Fact Verification Accuracy；
- Unsupported Claim / Invalid Evidence Rate；
- 代表 Case 全链路通过。

---

## T026 Serving benchmark and final acceptance

**Status:** TODO  
**Depends on:** T022, T023, T024, T025

**Acceptance:**
- 记录至少 latency、throughput、GPU memory（真实环境可测时）；
- 汇总模型/RAG/Agent 指标；
- 将实际完成与设计项区分，不填写未跑出的虚构结果；
- README 更新到可复现状态。
