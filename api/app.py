"""质检系统的 FastAPI 入口。"""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.service import AnalysisService, build_default_service
from db.models import ReviewDecision, ReviewRecord
from db.repository import SQLiteRepository
from schemas.conversation import Conversation
from schemas.finding import Finding
from schemas.qa_rule import QARule


class AnalyzeRequest(BaseModel):
    """质检请求。"""

    case_id: str
    conversation: Conversation
    rules: list[QARule]


class AnalyzeResponse(BaseModel):
    """质检响应。"""

    case_id: str
    findings: list[Finding]
    agent_runs: list[dict[str, Any]]


class ReviewRequest(BaseModel):
    """人工复核请求。"""

    review_id: str
    finding_id: str
    decision: ReviewDecision
    corrected_finding: Finding | None = None


def create_app(
    service: AnalysisService | None = None,
    repository: SQLiteRepository | None = None,
) -> FastAPI:
    """创建可注入测试依赖的 FastAPI app。"""

    if service is None:
        service = build_default_service()
    if repository is None:
        repository = service.repository

    app = FastAPI(title="Customer QA Agent")

    @app.post("/qa/analyze", response_model=AnalyzeResponse)
    def analyze(request: AnalyzeRequest) -> dict[str, Any]:
        return service.analyze(
            case_id=request.case_id,
            conversation=request.conversation,
            rules=request.rules,
        )

    @app.post("/reviews")
    def save_review(request: ReviewRequest) -> dict[str, str]:
        if (
            request.decision is ReviewDecision.CORRECTION
            and request.corrected_finding is None
        ):
            raise HTTPException(
                status_code=400,
                detail="correction review requires corrected_finding",
            )

        repository.save_review(
            ReviewRecord(
                review_id=request.review_id,
                finding_id=request.finding_id,
                decision=request.decision,
                corrected_finding=request.corrected_finding,
            )
        )
        return {"status": "saved", "review_id": request.review_id}

    return app