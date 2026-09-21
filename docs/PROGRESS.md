# PROGRESS.md

## Current milestone

**M1：仓库与核心数据契约**

## Completed

- 明确项目性质：学校承接企业横向项目。
- 明确个人角色：整体负责人。
- 明确企业侧与项目组技术边界。
- 明确核心主链路：SFT → Findings → Claim-level Agent → Tool/RAG → Evidence → Feedback → vLLM。
- 完成 T001：建立 Python package 骨架、最小项目配置、pytest 配置、导入测试和开发环境忽略规则。
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
- `python -m pytest` 实际执行结果为 `13 passed`。
- 暂无业务代码完成；Conversation、Rule、Finding、Evidence、Agent、RAG、模型调用、训练和 Serving 均未实现。

当前不要声称已经完成：
- Conversation/Rule/Finding Schema；
- LLM 调用；
- RAG；
- Agent；
- LoRA-SFT；
- vLLM 部署。

## Current repository state

```text
T001 Python project skeleton is initialized and verified.
Business source directories are importable packages, but contain no business logic yet.
```

## Current constraints

- 从企业标准化 Conversation 开始。
- 第一版使用受控 Mock / 测试业务接口。
- 动态业务知识进入 RAG，不硬编码进 SFT。
- Agent 在 Finding/Claim 粒度触发。
- 第一版外部能力只抽象为 Order Context 与 Business Knowledge 两类。
- Evidence 中能确定性验证的内容优先 Python 校验。

## Development environment

- Python: `>=3.10`，当前验证环境为 Python `3.12.7`。
- 创建隔离环境后安装开发依赖：`python -m pip install -e ".[dev]"`。
- 运行测试：`python -m pytest`。

## Next task

`T002 Conversation Schema`

等待项目负责人的下一步指令后再实现；本任务未提前进入 T002。
