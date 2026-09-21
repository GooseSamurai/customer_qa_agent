"""SFT 候选导出测试。"""

import json

from db.models import ReviewDecision, ReviewRecord
from db.repository import SQLiteRepository
from feedback.export_sft import export_sft_candidates
from schemas.conversation import Conversation
from schemas.finding import Finding
from tests.fixtures.cases import CASE_A


def sample_finding() -> Finding:
    """返回测试 Finding。"""

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


def test_export_sft_candidates_excludes_false_positive(tmp_path) -> None:
    """confirmed 和 correction 应导出，false_positive 不导出。"""

    repository = SQLiteRepository(tmp_path / "qa.db")
    conversation = Conversation.model_validate(CASE_A["conversation"])
    finding = sample_finding()
    repository.save_case("case-1", conversation)
    finding_id = repository.save_findings("case-1", [finding])[0]
    corrected = finding.model_copy(update={"reason": "复核修正原因。"})

    repository.save_review(
        ReviewRecord(
            review_id="review-confirmed",
            finding_id=finding_id,
            decision=ReviewDecision.CONFIRMED,
        )
    )
    repository.save_review(
        ReviewRecord(
            review_id="review-correction",
            finding_id=finding_id,
            decision=ReviewDecision.CORRECTION,
            corrected_finding=corrected,
        )
    )
    repository.save_review(
        ReviewRecord(
            review_id="review-false",
            finding_id=finding_id,
            decision=ReviewDecision.FALSE_POSITIVE,
        )
    )

    output = tmp_path / "sft_candidates.jsonl"
    count = export_sft_candidates(repository, output)

    assert count == 2
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert {row["decision"] for row in rows} == {"confirmed", "correction"}
    assert rows[1]["finding"]["reason"] == "复核修正原因。"