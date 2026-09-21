# 电商客服智能质检大模型与 Agent 系统

学校承接的企业横向项目。企业侧已有客服数据中台、订单/售后系统、人工质检制度和质检工作台，本仓库负责智能质检算法层。

## 项目目标

在标准化客服会话基础上，建设一条可审计的大模型质检链路：

```text
Conversation
→ Dynamic QA Rules
→ LoRA-SFT QA Model
→ Findings
→ Finding/Claim Router
→ Order Context Tool / Business Knowledge RAG
→ Grounded Re-evaluation
→ Evidence Verification
→ Review
→ Bad Case → SFT Feedback
```

模型部署通过独立推理服务完成，目标运行时为 vLLM。

## 业务范围

覆盖典型电商客服场景：

- 商品咨询
- 物流查询
- 退换货 / 售后
- 退款进度
- 优惠券 / 活动价格
- 投诉与升级

重点质检维度包括服务态度、推诿/敷衍、诉求理解、问题解决完整性、业务解释准确性、无依据承诺、流程规范和投诉升级规范。

## 技术边界

企业侧提供：
- 标准化客服会话；
- 质检规则与人工复核样本；
- 订单/售后测试接口；
- 售后、活动、客服 SOP 等业务文档。

本仓库负责：
- SFT 数据构建与 LoRA-SFT；
- 多 Finding 结构化输出；
- Claim 级事实核验 Agent；
- 订单上下文 Tool；
- Business Knowledge RAG；
- Evidence Verification；
- 人工反馈到 SFT 数据回流；
- vLLM 推理服务与分层评测。

## 核心数据对象

- `Conversation`：标准化客服会话。
- `QARule`：企业当前启用的质检规则。
- `Finding`：一次会话中的一条独立质检发现。
- `Evidence`：支撑 Finding 的可追溯证据。

一段 Conversation 可以产生 0~N 个 Findings。只有具体 Finding 中存在需要外部验证的 Claim 时，才进入 Agent 事实核验。

## 仓库结构

```text
customer_qa_agent/
├── AGENTS.md
├── README.md
├── docs/
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   ├── PROGRESS.md
│   └── TASKS.md
├── api/
├── schemas/
├── model/
│   ├── prompt.py
│   ├── qa_model.py
│   └── output_schema.py
├── agent/
│   ├── state.py
│   ├── workflow.py
│   ├── router.py
│   └── grounded_judge.py
├── tools/
│   ├── order_context.py
│   └── knowledge_tool.py
├── rag/
│   ├── ingest.py
│   ├── retrieve.py
│   └── rerank.py
├── evidence/
│   └── verifier.py
├── training/
│   ├── build_sft_data.py
│   └── train_lora.py
├── feedback/
│   └── export_sft.py
├── serving/
│   ├── vllm_client.py
│   └── service.py
├── evaluation/
├── db/
└── tests/
```

## 当前状态

当前仓库已经完成 T001-T026：

- 标准化数据契约；
- 真实中文 RAG：LangChain 切分、BGE Embedding、Chroma、BGE Reranker；
- 本地 Qwen 推理和 Grounded Judge；
- LangGraph Finding 工作流；
- SQLite、FastAPI、人工复核和 SFT 反馈导出；
- SFT 数据构建和 LoRA-SFT 训练入口；
- vLLM HTTP 客户端和服务适配；
- Model、RAG、Agent、Evidence、Serving 分层评测。

当前真实评测结果见 `evaluation/REPORT.md`。正式规模 LoRA-SFT、真实 vLLM 部署和量化仍属于后续工作。

## 运行与复现

安装开发依赖：

```powershell
python -m pip install -e ".[dev]"
```

运行全部测试：

```powershell
python -m pytest
```

查看文档切分：

```powershell
python -m rag.ingest data/knowledge/documents.json
```

运行 RAG 与 Serving 评测：

```powershell
python -m evaluation.rag_eval
python -m evaluation.serving_benchmark
```

## 文档导航

- `AGENTS.md`：Codex/开发代理长期工作规则。
- `docs/REQUIREMENTS.md`：系统必须做什么、不做什么、验收标准。
- `docs/ARCHITECTURE.md`：模块职责、依赖方向和公共数据对象。
- `docs/DECISIONS.md`：关键技术决策及原因。
- `docs/TASKS.md`：可逐个执行的实现任务。
- `docs/PROGRESS.md`：当前真实实现状态。
