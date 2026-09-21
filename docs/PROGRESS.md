# PROGRESS.md

## Current milestone

**M1：仓库与核心数据契约**

## Completed

- 明确项目性质：学校承接企业横向项目。
- 明确个人角色：整体负责人。
- 明确企业侧与项目组技术边界。
- 明确核心主链路：SFT → Findings → Claim-level Agent → Tool/RAG → Evidence → Feedback → vLLM。
- 完成 T001：建立 Python package 骨架、最小项目配置、pytest 配置、导入测试和开发环境忽略规则。
- 完成 T002：定义标准化 Conversation 与 Message Schema，并覆盖正常和异常输入测试。
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
- `python -m pytest -p no:cacheprovider` 实际执行结果为 `17 passed`：T002 4 个测试加 T001 原有 13 个测试。
- QARule、Finding、Evidence、Agent、RAG、模型调用、训练和 Serving 仍未实现。

当前不要声称已经完成：
- QARule/Finding/Evidence Schema；
- LLM 调用；
- RAG；
- Agent；
- LoRA-SFT；
- vLLM 部署。

## Current repository state

```text
T001 Python project skeleton is initialized and verified.
T002 standardized Conversation and Message schemas are implemented and tested.
Rule, Finding, Evidence, Agent, RAG, training, and serving are not implemented yet.
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

- Python: `>=3.10`。`llamafactory` 环境使用 Python `3.11.15`、pytest `9.1.1` 完成 T002 验证；CI 同时覆盖 Python 3.10 和 3.12。
- 创建隔离环境后安装开发依赖：`python -m pip install -e ".[dev]"`。
- 运行测试：`python -m pytest`。

## Next task

`T003 QA Rule Schema`

等待项目负责人的下一步指令后再实现；本任务未提前进入 T003。
