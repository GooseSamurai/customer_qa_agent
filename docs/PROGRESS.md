# PROGRESS.md

## Current milestone

**M5：API、持久化与人工反馈**

## Completed

- 明确项目性质：学校承接企业横向项目。
- 明确个人角色：整体负责人。
- 明确企业侧与项目组技术边界。
- 明确核心主链路：SFT → Findings → Claim-level Agent → Tool/RAG → Evidence → Feedback → vLLM。
- 完成 T001：建立 Python package 骨架、最小项目配置、pytest 配置、导入测试和开发环境忽略规则。
- 完成 T002：定义标准化 Conversation 与 Message Schema，并覆盖正常和异常输入测试。
- 完成 T003：定义 QARule 质检规则数据结构，并覆盖正常和异常输入测试。
- 完成 T004：定义 Finding 与 Conversation/Order/Knowledge Evidence Schema，并覆盖四类 required_evidence 路由表达及异常输入。
- 完成 T005：建立 Case A/B/C 和 Mock 规则、订单、知识输入数据。
- 完成 T006：实现会话证据校验，覆盖消息不存在、角色错误和原话不存在。
- 完成 T007：实现订单上下文 Mock 工具，覆盖正常查询、字段筛选和订单不存在。
- 完成 T008：建立六份电商平台业务知识样例和 Metadata，并使用 LangChain MarkdownHeaderTextSplitter 完成结构化切分。
- 完成 T009：接入 BAAI/bge-small-zh-v1.5 中文 Embedding、Chroma 向量库、Metadata Filter 和过期文档排除。
- 完成 T010：接入 BAAI/bge-reranker-base CrossEncoder 对候选知识片段二次重排。
- 完成 T011：将 RAG 封装为业务知识工具，并输出可追溯的 KnowledgeEvidence。
- 完成 T012-T013：建立质检 Prompt、结构化 Finding 输出、供应商无关模型封装，并接入本地 Qwen3-VL-2B-Instruct 真实推理。
- 完成 T014-T015：实现单 Finding 路由和基于已有证据的受约束复判，真实 Qwen 已完成 Case B 复判验证。
- 完成 T016：使用 LangGraph 串起会话证据校验、Finding 路由、订单/知识取证、Grounded Judge 和人工复核分支。
- 建立仓库级 Vibe Coding 文档体系：
  - `AGENTS.md`
  - `README.md`
  - `docs/REQUIREMENTS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DECISIONS.md`
  - `docs/PROGRESS.md`
  - `docs/TASKS.md`

## Verified implementation

- T001 工程骨架已完成并通过验证：12 个业务 package 可正常导入。
- T002 Conversation Schema 已完成并通过验证。
- T003 QARule Schema 已完成并通过验证。
- T004 Finding 与 Evidence Schema 已完成并通过验证。
- T001-T016 已验证，完整测试 `63 passed`。真实 RAG、本地 Qwen 推理、Finding Router、Grounded Judge 和 LangGraph 工作流均有测试或实际运行验证。
- RAG 和本地 Qwen 推理已接入；Agent 工作流、训练、vLLM/量化部署和持久化知识索引仍未实现。

当前不要声称已经完成：
- vLLM/量化部署；
- 生产级 RAG 平台能力（持久化索引、权限、批量评测等）；
- 完整 Agent Workflow；
- LoRA-SFT；
- vLLM 部署。

## Current repository state

```text
T001-T004 schemas are implemented and tested.
T005-T007 evidence fixtures, verification, and order-context tools are implemented and tested.
T008-T011 implement a real local RAG pipeline with LangChain Markdown splitting, BGE embeddings, Chroma, and BGE reranking.
T012-T015 implement the QA model contract, local Qwen inference client, Finding router, and grounded re-evaluation.
T016 implements the LangGraph workflow for direct, order, knowledge, combined, and human-review paths.
Training, persistence/API, vLLM/quantized serving, and persistent knowledge indexing are not implemented yet.
```

## Current constraints

- 从企业标准化 Conversation 开始。
- 第一版使用受控 Mock / 测试业务接口。
- 动态业务知识进入 RAG，不硬编码进 SFT。
- Agent 在 Finding/Claim 粒度触发。
- 第一版外部能力只抽象为 Order Context 与 Business Knowledge 两类。
- Evidence 中能确定性验证的内容优先 Python 校验。

## Git and CI

- 本地 Git 仓库已初始化，默认分支为 `main`。
- GitHub Public 仓库：`https://github.com/GooseSamurai/customer_qa_agent`。
- 本地远端名 `origin` 指向 GitHub 仓库，`main` 已建立 tracking。
- 首个本地提交：`b203b2d chore: initialize project skeleton and CI`。
- GitHub Actions CI 已配置：`.github/workflows/ci.yml`。
- CI 使用 Python 3.10 和 3.12 分别执行全部测试。
- 首次远端 CI 运行成功：run `35564478483`。
- `main` 已启用保护：必须通过 Pull Request、必须通过两个 CI 检查、禁止强制推送、禁止删除。
- CD 尚未实现，等待明确的部署目标和服务制品。

## Development environment

- Python: `>=3.10`。T002-T015 使用 `llamafactory` 环境 Python `3.11.15` 和 Python `3.12.7` 完成验证；本地 Qwen 权重位于 `G:\LLM\modelscope\hub\models\qwen\Qwen3-VL-2B-Instruct`。
- 创建隔离环境后安装开发依赖：`python -m pip install -e ".[dev]"`。
- 运行测试：`python -m pytest`。

## Next task

`T017 Minimal persistence layer`

等待项目负责人的下一步指令后再实现；本任务未提前进入 T017。
