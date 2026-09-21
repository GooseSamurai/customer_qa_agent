# REQUIREMENTS.md

## 1. 项目目标

建设企业电商客服智能质检算法层。系统消费企业已经标准化的客服会话和质检规则，使用领域大模型完成复杂语义质检；对涉及实时业务事实或动态知识的 Finding，通过受控 Agent 调用业务 Tool / RAG 取证，最终输出可追溯的结构化质检结果。

项目重点体现：LLM 微调、Agent、RAG、Evidence Grounding、模型服务和评测。

## 2. 上游输入

### 2.1 标准化 Conversation

系统直接接收企业统一会话格式，不负责淘宝、京东、拼多多、抖音等平台原始协议解析。

最小字段：

```text
conversation_id
channel
customer_id
agent_id
order_ids
start_time
messages[]
  message_id
  role
  timestamp
  text
```

### 2.2 QA Rules

企业运营/质检团队维护规则，项目组消费已结构化规则：

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

### 2.3 外部能力

企业提供或测试环境模拟：
- 订单/物流/退款/售后等业务上下文查询接口；
- 售后政策、客服 SOP、活动规则、价格/优惠等业务文档；
- 历史人工复核结果。

## 3. 功能需求

### FR-01 Conversation 校验

系统必须能够校验标准化 Conversation：必填字段、消息角色、消息列表非空、message_id 唯一、时间字段格式等。

### FR-02 动态规则输入

系统必须能够加载当前启用的 QA Rules，并将规则版本与一次质检运行关联。

### FR-03 多 Finding 质检

一个 Conversation 必须支持输出 0~N 个 Findings。不同问题不得强行压缩成一个总标签。

### FR-04 Finding 结构化输出

每个 Finding 至少包含：

```text
rule_id
risk_type
severity
reason
conversation_evidence
requires_external_verification
claim（可空）
required_evidence
confidence（如使用）
```

### FR-05 Conversation Evidence

模型引用客服原文时，必须绑定 `message_id + quote`，并能够由程序验证 quote 是否真实存在于该客服消息。

### FR-06 外部事实触发

系统必须在 Finding 级判断是否需要外部事实。不得把整条 Conversation 粗略分成“走 Agent / 不走 Agent”两类。

### FR-07 Agent 路由

根据 Finding 的 `required_evidence` 决定需要：
- 不调用外部能力；
- 查询 Order Context；
- 查询 Business Knowledge；
- 同时获取两类证据；
- 无法判断时转人工/异常路径。

### FR-08 Order Context Tool

系统需要一个稳定接口查询与当前订单相关的结构化业务事实，例如订单、物流、退款、售后、优惠上下文。开发阶段允许使用 Mock / SQLite / 测试 API。

### FR-09 Business Knowledge RAG

系统必须支持对动态业务文档进行：

```text
结构化切分
Metadata 管理
Metadata Filter
向量召回
Rerank
返回可追溯 source_id / chunk_id
```

### FR-10 Grounded Re-evaluation

当获取外部证据后，系统必须围绕原 Finding / Claim 进行受约束复判，而不是重新自由分析整个业务数据库。

### FR-11 Evidence Verification

系统必须对至少以下内容做确定性验证：
- 会话 quote 是否真实存在；
- order_id / source_id 是否一致；
- policy/chunk 是否来自本次检索；
- 生效时间等明确字段是否满足规则；
- 必要 Evidence 是否缺失。

### FR-12 人工复核反馈

支持将人工结果区分为：

```text
confirmed
false_positive
correction
```

并能将合格的复核样本导出为后续 SFT 候选数据。

### FR-13 SFT

系统必须提供离线 SFT 数据构建和 LoRA-SFT 训练入口。SFT 学习企业质检能力、Finding Schema、Evidence 定位和 Claim 触发，不把频繁变化的活动政策硬编码进模型参数。

### FR-14 Serving

微调模型必须能够通过独立推理服务调用。目标实现为 vLLM 客户端/服务集成，并与业务 Agent 解耦。

### FR-15 分层评测

必须能够分别评估：
- QA Model；
- RAG；
- Agent routing / tool use；
- Evidence；
- Serving 性能。

## 4. 非功能需求

### NFR-01 可审计

最终 Finding 能追溯到：
- 原始客服消息；
- 使用的 Rule 版本；
- Tool 返回；
- RAG source/chunk；
- 模型/服务版本。

### NFR-02 可测试

业务逻辑需可在不连接真实企业生产系统时通过 Mock 数据进行单元与集成测试。

### NFR-03 可解释

核心路由、Evidence 校验和异常路径优先使用明确代码逻辑，避免不必要的自由 LLM 决策。

### NFR-04 模块解耦

训练、推理、RAG、Tool、Agent、API、DB 之间保持清晰依赖边界。

## 5. 第一阶段不在范围内

当前仓库不负责：
- 多渠道原始客服数据采集 / ETL；
- 企业订单/售后系统实现；
- 完整人工质检后台和前端看板；
- 企业权限、SSO、生产鉴权体系；
- 自动在线训练；
- 通用多 Agent 协作；
- 自由 ReAct / 长规划 Agent；
- AWQ、TensorRT-LLM、多机多卡、Kubernetes 等复杂部署优化。

## 6. 代表性验收 Case

### Case A：纯语义推诿

```text
客户：我已经问三次了，你们到底怎么处理？
客服：这个不归我们管，你自己联系物流。
```

期望：
- 输出推诿 Finding；
- `requires_external_verification=false`；
- quote 可程序验证；
- 不调用业务 Tool。

### Case B：售后资格

```text
客户：耳机坏了，买了十几天，可以退吗？
客服：超过 7 天都不能退。
```

期望：
- 输出潜在业务解释错误 Finding；
- 抽取 Claim；
- 需要 order + knowledge Evidence；
- 查询订单签收/品类；
- 检索当前有效售后规则；
- 根据证据完成复判。

### Case C：退款到账承诺

```text
客户：这笔退款什么时候到账？
客服：今晚肯定到账。
```

期望：
- 识别具体订单的确定性承诺；
- 查询 Order Context；
- 当业务系统没有该到账时间依据时，输出无依据承诺 Finding。

## 7. 第一阶段完成标准

第一阶段不是“整个生产平台上线”，而是完成一条可复现、可测试的算法闭环：

```text
标准化 Conversation
→ QA Findings
→ Finding/Claim Router
→ Mock Order Tool / Business Knowledge RAG
→ Grounded Judge
→ Evidence Verification
→ 结构化结果
→ Review Feedback
```

随后再接入 SFT 和 vLLM 部署。
