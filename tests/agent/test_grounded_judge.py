"""Grounded Judge 测试。"""

import json

import pytest

from agent.grounded_judge import GroundedJudge
from model.qa_model import InvalidModelOutput
from schemas.evidence import KnowledgeEvidence, OrderEvidence
from schemas.finding import Finding


class FakeModelClient:
    """返回预设文本，记录收到的 Prompt。"""

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompt = ""

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return self.response


def original_finding() -> Finding:
    """返回一个需要订单和知识核验的 Finding。"""

    return Finding.model_validate(
        {
            "rule_id": "rule-after-sale",
            "risk_type": "policy_explanation_error",
            "severity": "high",
            "reason": "客服可能错误解释售后资格。",
            "conversation_evidence": [
                {"message_id": "msg-b-002", "quote": "超过 7 天都不能退"}
            ],
            "requires_external_verification": True,
            "claim": "耳机购买十几天后是否可以退货。",
            "required_evidence": ["order_context", "business_knowledge"],
            "external_evidence": [],
        }
    )


def evidence() -> list:
    """返回订单和知识证据。"""

    return [
        OrderEvidence(
            order_id="order-001",
            field="received_days",
            value=12,
            queried_at="2026-09-21T11:01:00+08:00",
        ),
        KnowledgeEvidence(
            source_id="return_exchange_policy",
            chunk_id="return_exchange_policy-chunk-2",
            text="质量问题退货的处理方式以审核结果为准。",
            metadata={"category": "after_sale"},
        ),
    ]


def test_grounded_judge_returns_corrected_finding() -> None:
    """Judge 应返回模型修正后的 Finding。"""

    finding = original_finding()
    corrected = finding.model_copy(
        update={
            "reason": "客服直接认定不能退货，未结合具体售后规则。",
            "external_evidence": evidence(),
        }
    )
    client = FakeModelClient(corrected.model_dump_json())
    judge = GroundedJudge(client)

    result = judge.judge(finding, evidence())

    assert result.reason == "客服直接认定不能退货，未结合具体售后规则。"
    assert result.external_evidence == evidence()
    assert finding.claim in client.prompt
    assert "return_exchange_policy-chunk-2" in client.prompt


def test_grounded_judge_rejects_invalid_json() -> None:
    """模型返回非法 JSON 时，应抛出明确异常。"""

    judge = GroundedJudge(FakeModelClient("not json"))

    with pytest.raises(InvalidModelOutput):
        judge.judge(original_finding(), evidence())