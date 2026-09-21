"""FastAPI 接口契约测试。"""

from fastapi.testclient import TestClient

from api.app import create_app
from db.repository import SQLiteRepository
from schemas.conversation import Conversation
from schemas.finding import Finding
from tests.fixtures.cases import CASE_A, MOCK_RULES


class FakeService:
    """不执行真实 Agent 的测试服务。"""

    def __init__(self, repository: SQLiteRepository) -> None:
        self.repository = repository

    def analyze(self, case_id, conversation, rules) -> dict:
        return {"case_id": case_id, "findings": [], "agent_runs": []}


def sample_finding() -> Finding:
    """返回一条可保存的 Finding。"""

    return Finding.model_validate(
        {
            "rule_id": "rule-blame",
            "risk_type": "blame_shifting",
            "severity": "high",
            "reason": "客服推诿客户。",
            "conversation_evidence": [
                {"message_id": "msg-a-002", "quote": "这个不归我们管"}
            ],
            "requires_external_verification": False,
            "claim": None,
            "required_evidence": [],
            "external_evidence": [],
        }
    )


def test_analyze_endpoint_returns_standard_response(tmp_path) -> None:
    """质检接口应返回 case_id、findings 和 agent_runs。"""

    repository = SQLiteRepository(tmp_path / "qa.db")
    client = TestClient(
        create_app(service=FakeService(repository), repository=repository)
    )

    response = client.post(
        "/qa/analyze",
        json={
            "case_id": "case-1",
            "conversation": CASE_A["conversation"],
            "rules": MOCK_RULES[:1],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "case-1",
        "findings": [],
        "agent_runs": [],
    }


def test_review_endpoint_saves_decision(tmp_path) -> None:
    """复核接口应保存 confirmed 结果。"""

    repository = SQLiteRepository(tmp_path / "qa.db")
    conversation = Conversation.model_validate(CASE_A["conversation"])
    repository.save_case("case-1", conversation)
    finding_id = repository.save_findings("case-1", [sample_finding()])[0]
    client = TestClient(
        create_app(service=FakeService(repository), repository=repository)
    )

    response = client.post(
        "/reviews",
        json={
            "review_id": "review-1",
            "finding_id": finding_id,
            "decision": "confirmed",
        },
    )

    assert response.status_code == 200
    assert repository.get_review("review-1").decision.value == "confirmed"


def test_correction_requires_corrected_finding(tmp_path) -> None:
    """correction 复核必须提供修正后的 Finding。"""

    repository = SQLiteRepository(tmp_path / "qa.db")
    client = TestClient(
        create_app(service=FakeService(repository), repository=repository)
    )

    response = client.post(
        "/reviews",
        json={
            "review_id": "review-1",
            "finding_id": "finding-1",
            "decision": "correction",
        },
    )

    assert response.status_code == 400