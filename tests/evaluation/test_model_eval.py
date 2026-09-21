"""QA Model 评测测试。"""

from evaluation.model_eval import evaluate_model
from schemas.finding import Finding
from tests.fixtures.cases import CASE_A, MOCK_RULES


class FakeQAModel:
    def analyze(self, conversation, rules) -> list[Finding]:
        return [
            Finding.model_validate(
                {
                    "rule_id": "rule-blame",
                    "risk_type": "blame_shifting",
                    "severity": "high",
                    "reason": "客服推诿。",
                    "conversation_evidence": [
                        {"message_id": "msg-a-002", "quote": "这个不归我们管"}
                    ],
                    "requires_external_verification": False,
                    "claim": None,
                    "required_evidence": [],
                    "external_evidence": [],
                }
            )
        ]


def test_model_eval_computes_all_metrics() -> None:
    cases = [
        {
            "conversation": CASE_A["conversation"],
            "rules": MOCK_RULES,
            "expected_labels": ["rule-blame|blame_shifting"],
            "expected_external_verification": False,
            "expected_message_id": "msg-a-002",
            "expected_quote": "这个不归我们管",
        }
    ]

    report = evaluate_model(FakeQAModel(), cases)

    assert report["finding_classification_f1"] == 1.0
    assert report["external_verification_trigger_f1"] == 1.0
    assert report["evidence_localization_accuracy"] == 1.0
    assert report["schema_success_rate"] == 1.0