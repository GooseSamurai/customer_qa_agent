# T017-T019 持久化、API 与人工反馈：业务和设计学习笔记

## 1. 这组任务解决什么问题

T017-T019 把前面的质检能力接入到可保存、可调用、可反馈的闭环：

```text
Conversation + QARule
→ FastAPI 接口
→ QA Model + Agent Workflow
→ 保存 case / finding / evidence / agent run
→ 人工复核
→ 导出 SFT 候选
```

它们不负责自动训练模型，也不实现企业前端页面。

## 2. T017：最小持久化层

### 2.1 为什么需要持久化

质检过程会产生：

- 输入 Conversation；
- 模型产生的 Finding；
- 订单和知识 Evidence；
- Agent 每一步的运行结果；
- 人工复核结果。

如果只存在内存中，服务重启后所有审计链路都会丢失。

### 2.2 为什么使用 SQLite

当前阶段只需要保存最小过程数据，标准库 `sqlite3` 已经足够。

没有引入 SQLAlchemy，原因是：

- 当前表结构很小；
- 不需要复杂 ORM 关系；
- 新手更容易理解；
- 测试可以直接使用临时 SQLite 文件。

### 2.3 五个最小表

```text
qa_cases       保存 Conversation
qa_findings    保存 Finding
qa_evidence    保存订单/知识 Evidence
agent_runs     保存一次 Agent workflow 的运行状态
qa_reviews     保存人工复核结果
```

Finding 和 Evidence 的内容先以 JSON 保存，保留完整审计信息。后续如果需要按单字段查询，再考虑拆成更多列。

### 2.4 Repository 的职责

`SQLiteRepository` 只负责：

- 建表；
- 保存；
- 读取；
- 不调用 Router；
- 不调用 LLM；
- 不决定业务路径。

数据库不知道“应该查订单还是知识”，它只接收上层已经决定好的数据。

## 3. T018：质检 API

### 3.1 服务分层

```text
api/app.py
    HTTP 请求和响应

api/service.py
    组合 QA Model、Agent Workflow、Repository

agent / model / rag / tools
    核心算法能力
```

API 不直接写 RAG、Tool 或 LLM 细节，只负责接收请求并调用 application service。

### 3.2 质检接口

```text
POST /qa/analyze
```

输入：

- `case_id`
- `Conversation`
- `QARule` 列表

输出：

- `case_id`
- 最终 Findings
- Agent Run 摘要

内部流程：

```text
QAModel.analyze
→ LangGraph run_workflow
→ 保存 case / finding / evidence / agent run
→ 返回标准结果
```

### 3.3 人工复核接口

```text
POST /reviews
```

输入：

- review_id
- finding_id
- decision
- corrected_finding，correction 时必填

如果 correction 没有修正 Finding，接口返回 `400`。

### 3.4 为什么使用 `create_app()`

`create_app()` 允许测试注入 Fake Service 和临时 SQLite，不要求在 API 测试中加载真实 Qwen 或真实 RAG。

真实运行时使用 `build_default_service()`，组合本地 Qwen、真实 RAG 和 SQLite。

## 4. T019：人工反馈和 SFT 候选

### 4.1 三种复核结果

```text
confirmed
    人工确认原 Finding 正确

false_positive
    人工确认原 Finding 错报

correction
    人工确认有问题，但修正了 Finding
```

### 4.2 哪些结果进入 SFT 候选

```text
confirmed  → 导出
correction → 导出修正后的 Finding
false_positive → 不导出
```

原因是：

- confirmed 可以作为正例；
- correction 可以作为修正样本；
- false_positive 表示模型误报，当前阶段不能直接作为正例训练，否则会把错误答案教给模型。

### 4.3 导出格式

`export_sft_candidates()` 输出 JSONL，每行是一个候选样本：

```text
review_id
decision
conversation
finding
```

它只生成候选数据，不自动启动训练。这样可以把数据清洗、人工审核和训练入口解耦。

## 5. 完整数据流

### 在线质检

```text
POST /qa/analyze
→ AnalysisService
→ QAModel
→ Agent Workflow
→ Repository
→ 返回 findings + agent_runs
```

### 人工反馈

```text
POST /reviews
→ 保存 ReviewRecord
→ export_sft_candidates
→ JSONL 候选文件
```

## 6. 业务场景与处理

### 6.1 人工确认模型正确

```text
decision = confirmed
```

原 Finding 保留，导出 SFT 候选。

### 6.2 人工发现模型误报

```text
decision = false_positive
```

不导出为 SFT 候选，避免把误报当正例。

### 6.3 人工修正模型原因

```text
decision = correction
corrected_finding = 修正后的 Finding
```

导出时使用修正后的 Finding。

### 6.4 订单或知识 Evidence 获取失败

Agent Workflow 已进入 `human_review`，API 仍然可以保存 Agent Run，人工通过复核接口决定最终结果。

### 6.5 服务重启后需要看历史结果

从 SQLite Repository 读取 case、finding、evidence、agent run 和 review，不需要从聊天上下文中重新拼接。

## 7. 真实面试问题

### 问题 1：为什么持久化层不直接调用 Agent 或 Tool？

**回答：**

数据库只负责保存事实。如果让 Repository 决定路由或调用工具，数据层会承担业务决策，测试和替换都会变困难。当前设计让 Agent 负责决策，Repository 只接收结果。

### 问题 2：为什么选择 SQLite，而不是直接上 PostgreSQL？

**回答：**

当前项目是小规模算法闭环，SQLite 足以验证表和 Repository 边界，部署成本低。真正面向企业并发时，再替换为 PostgreSQL 或其他正式数据库，接口可以保持相似。

### 问题 3：为什么 API 不直接把 QA Model 和 Tool 写在路由函数里？

**回答：**

路由函数只处理 HTTP 适配，application service 负责组合算法流程。这样测试 API 时可以注入 Fake Service，不需要每次加载 Qwen 和向量库。

### 问题 4：为什么 `false_positive` 不导出到 SFT？

**回答：**

SFT 的目标是教模型正确的质检模式。直接把误报当正例训练，会把错误行为固化进模型。它更适合进入错误分析、负例或后续偏好优化流程。

### 问题 5：为什么 `correction` 要保存完整 Finding？

**回答：**

人工修正的原因、严重程度、Claim 或 Evidence 都可能变化。只保存一句修正文本不足以还原最终标签，也无法直接构造训练样本。

### 问题 6：怎样避免反馈直接污染训练？

**回答：**

Review 先写入独立表，SFT 导出只生成候选文件，不自动触发训练。后续还需要数据清洗、抽样审核和训练配置确认。

## 8. 学习检查与答案

### 1. `qa_cases` 保存什么？

保存标准化 Conversation，以及对应的 case_id。

### 2. `qa_findings` 保存什么？

保存模型输出或后续修正后的 Finding 及其 case_id。

### 3. `agent_runs` 为什么重要？

它记录某次 Finding 走过了什么路径、是否完成、错误是什么，用于审计和排查。

### 4. API 中 app 和 service 的职责分别是什么？

app 负责 HTTP 请求/响应，service 负责组合模型、工作流和持久化。

### 5. `confirmed`、`false_positive`、`correction` 分别代表什么？

分别代表确认正确、确认误报、人工修正。

### 6. 为什么 correction 必须有 corrected_finding？

因为没有修正后的 Finding，后续导出无法确定应该训练什么结果。

### 7. 导出的 JSONL 中包含什么？

review_id、decision、conversation 和 finding。

### 8. T019 会自动启动训练吗？

不会。它只生成 SFT 候选数据，训练需要独立任务和人工确认。

## 9. 一句话总结

T017 用最小 SQLite Repository 保存完整质检过程，T018 用 FastAPI 提供质检和复核入口，T019 将 confirmed/correction 导出为 SFT 候选并排除 false_positive；这套设计把执行、持久化和训练数据反馈分开，便于审计、测试和后续演进。