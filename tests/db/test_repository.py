"""SQLite Repository 测试。"""

from db.models import AgentRunRecord, ReviewDecision, ReviewRecord
from db.repository import SQLiteRepository
from schemas.conversation import Conversation
from schemas.evidence import KnowledgeEvidence
from schemas.finding import Finding
from tests.fixtures.cases import CASE_A


def sample_finding() -> Finding:
    """返回一条测试 Finding。"""

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


def test_repository_saves_required_records(tmp_path) -> None:
    """Repository 应保存 case、finding、evidence、run 和 review。"""

    repository = SQLiteRepository(tmp_path / "qa.db")
    conversation = Conversation.model_validate(CASE_A["conversation"])
    finding = sample_finding()

    repository.save_case("case-1", conversation)
    finding_id = repository.save_findings("case-1", [finding])[0]
    evidence = KnowledgeEvidence(
        source_id="source-1",
        chunk_id="chunk-1",
        text="规则片段",
        metadata={"category": "after_sale"},
    )
    repository.save_evidence(finding_id, [evidence])
    repository.save_agent_run(
        AgentRunRecord(
            run_id="run-1",
            case_id="case-1",
            status="completed",
            state={"route": "direct"},
        )
    )
    repository.save_review(
        ReviewRecord(
            review_id="review-1",
            finding_id=finding_id,
            decision=ReviewDecision.CONFIRMED,
        )
    )

    assert repository.get_case("case-1") == conversation
    assert repository.get_finding(finding_id) == finding
    assert repository.get_agent_run("run-1").state == {"route": "direct"}
    assert repository.get_review("review-1").decision is ReviewDecision.CONFIRMED


def test_missing_finding_returns_none(tmp_path) -> None:
    """不存在的 Finding 不应伪造数据。"""

    repository = SQLiteRepository(tmp_path / "qa.db")

    assert repository.get_finding("missing") is None