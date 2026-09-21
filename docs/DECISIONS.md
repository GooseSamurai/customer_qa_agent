# DECISIONS.md

本文件只记录会长期影响实现的技术决策。完成任务、测试结果和日常进度不要写在这里。

---

## ADR-001 从标准化 Conversation 开始

**Status:** Accepted  
**Date:** 2026-09-21

### Context
企业已有多渠道客服数据中台，可以向算法系统提供统一会话数据。

### Decision
本仓库直接消费标准化 `Conversation`，不实现淘宝、京东、拼多多、抖音原始协议解析和 ETL。

### Consequence
开发和测试使用符合该 Schema 的脱敏/Mock 数据。

---

## ADR-002 SFT 学质检能力，不背动态业务知识

**Status:** Accepted  
**Date:** 2026-09-21

### Context
活动政策、优惠规则、新版售后政策会持续变化。

### Decision
LoRA-SFT 主要学习质检标签、语义边界、多 Finding、Evidence 定位、Claim 抽取和外部核验触发；动态业务知识放入 RAG / Tool。

### Consequence
政策更新通常不需要重新训练模型。

---

## ADR-003 一段 Conversation 可以生成多个 Findings

**Status:** Accepted  
**Date:** 2026-09-21

### Context
同一客服会话可能同时包含推诿、态度问题和业务解释错误。

### Decision
`Finding` 是独立质检结果单位，Conversation 与 Finding 为 1:N。

### Consequence
路由、Evidence、人工复核和指标尽可能在 Finding 粒度处理。

---

## ADR-004 Agent 在 Finding / Claim 级触发

**Status:** Accepted  
**Date:** 2026-09-21

### Context
并非所有问题都需要查询订单或政策。

### Decision
先由 QA Model 生成 Finding；只有 Finding 含待核验 Claim 时才进入外部取证流程。

### Consequence
减少不必要 Tool 调用，并可以单独评估 Trigger/Router Accuracy。

---

## ADR-005 第一版只抽象两类外部能力

**Status:** Accepted  
**Date:** 2026-09-21

### Decision
第一版使用：
- `Order Context Tool`：统一承载订单、物流、退款、售后、优惠等结构化业务上下文；
- `Business Knowledge Tool`：统一调用 RAG 查询动态业务知识。

### Consequence
不为每种业务字段创建一个独立 Tool，避免工具数量膨胀；后续确有独立权限/生命周期需求再拆分。

---

## ADR-006 确定性 Evidence 优先程序校验

**Status:** Accepted  
**Date:** 2026-09-21

### Decision
字符串存在性、ID 匹配、字段一致性、日期有效期、source trace 等明确规则由 Python 校验，不额外调用 LLM。

### Consequence
Verifier 更稳定、便宜、可测试；语义支持性判断仍可由 Grounded Judge 完成。

---

## ADR-007 LangGraph 用于受控工作流，不做自由 ReAct

**Status:** Accepted  
**Date:** 2026-09-21

### Context
质检系统强调可审计、低延迟和可控路径。

### Decision
LangGraph 主要用于 State、条件路由、节点隔离、错误/人工分支，不让 Agent 对每条会话自由规划任意步骤。

### Consequence
简单阶段可以先用 Python Router 实现，之后再无缝映射为 conditional edge。

---

## ADR-008 Review 数据可回流 SFT，但不自动在线训练

**Status:** Accepted  
**Date:** 2026-09-21

### Decision
人工 `confirmed / false_positive / correction` 经过清洗和审核后可以导出 SFT 候选数据；系统不自动触发线上重训。

### Consequence
训练数据质量与线上服务解耦，避免错误反馈直接污染模型。

---

## ADR-009 目标模型运行时使用 vLLM

**Status:** Accepted  
**Date:** 2026-09-21

### Decision
微调模型通过独立模型服务提供推理能力，目标运行时为 vLLM；业务 Agent 通过稳定 client/service 接口调用。

### Consequence
当前项目不同时扩展 AWQ、TensorRT-LLM、多机多卡和 Kubernetes 等复杂优化。
