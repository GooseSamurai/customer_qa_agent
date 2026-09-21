"""质检 API 的应用服务，负责组合已有 Agent 能力。"""

from datetime import date
from pathlib import Path
from typing import Any

from agent.grounded_judge import GroundedJudge
from agent.workflow import run_workflow
from db.models import AgentRunRecord
from db.repository import SQLiteRepository
from model.qa_model import QAModel
from rag.ingest import KnowledgeChunk, ingest_manifest
from schemas.conversation import Conversation
from schemas.qa_rule import QARule
from serving.local_qwen import LocalQwenClient


class AnalysisService:
    """运行质检工作流并保存最小过程数据。"""

    def __init__(
        self,
        qa_model: QAModel,
        judge: GroundedJudge,
        chunks: list[KnowledgeChunk],
        repository: SQLiteRepository,
        as_of: date | None = None,
    ) -> None:
        self.qa_model = qa_model
        self.judge = judge
        self.chunks = chunks
        self.repository = repository
        self.as_of = as_of

    def analyze(
        self,
        case_id: str,
        conversation: Conversation,
        rules: list[QARule],
    ) -> dict[str, Any]:
        """执行 QA Model 和 LangGraph workflow。"""

        findings = self.qa_model.analyze(conversation, rules)
        self.repository.save_case(case_id, conversation)
        finding_ids = self.repository.save_findings(case_id, findings)
        states = run_workflow(
            conversation=conversation,
            findings=findings,
            judge=self.judge,
            chunks=self.chunks,
            as_of=self.as_of,
        )

        run_results = []
        final_findings = []

        for index, (finding_id, state) in enumerate(zip(finding_ids, states), start=1):
            run_id = f"{case_id}-run-{index}"
            external_evidence = [
                *state.get("order_evidence", []),
                *state.get("knowledge_evidence", []),
            ]
            if external_evidence:
                self.repository.save_evidence(finding_id, external_evidence)

            final_finding = state.get("final_finding")
            if final_finding is not None:
                final_findings.append(final_finding.model_dump(mode="json"))

            run_state = {
                "finding_id": finding_id,
                "status": state.get("status"),
                "route": state.get("route").value if state.get("route") else None,
                "error": state.get("error"),
                "final_finding": (
                    final_finding.model_dump(mode="json")
                    if final_finding is not None
                    else None
                ),
            }
            self.repository.save_agent_run(
                AgentRunRecord(
                    run_id=run_id,
                    case_id=case_id,
                    status=state.get("status", "unknown"),
                    state=run_state,
                )
            )
            run_results.append({"run_id": run_id, **run_state})

        return {
            "case_id": case_id,
            "findings": final_findings,
            "agent_runs": run_results,
        }


def build_default_service(db_path: str | Path = "qa_agent.db") -> AnalysisService:
    """构建使用本地 Qwen 和真实 RAG 的默认服务。"""

    client = LocalQwenClient()
    return AnalysisService(
        qa_model=QAModel(client),
        judge=GroundedJudge(client),
        chunks=ingest_manifest(Path("data/knowledge/documents.json")),
        repository=SQLiteRepository(db_path),
        as_of=date.today(),
    )