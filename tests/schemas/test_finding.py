"""Finding 与 Evidence Schema 的正常和异常输入测试。"""

import pytest
from pydantic import ValidationError

from schemas.evidence import ConversationEvidence, KnowledgeEvidence, OrderEvidence
from schemas.finding import Finding, RequiredEvidence


def valid_finding_payload() -> dict:
    """返回一条不需要外部核验的纯语义 Finding。"""

    return {
        "rule_id": "rule-001",
        "risk_type": "blame_shifting",
        "severity": "high",
        "reason": "客服将客户问题直接推给物流方。",
        "conversation_evidence": [
            {
                "message_id": "msg-002",
                "quote": "这个不归我们管，你自己联系物流。",
            }
        ],
        "requires_external_verification": False,
        "claim": None,
        "required_evidence": [],
    }


def test_valid_direct_finding_is_parsed() -> None:
    """direct Finding 应生成嵌套会话证据并保持空的所需证据列表。"""

    finding = Finding.model_validate(valid_finding_payload())

    assert isinstance(finding.conversation_evidence[0], ConversationEvidence)
    assert finding.requires_external_verification is False
    assert finding.required_evidence == []
    assert finding.external_evidence == []


@pytest.mark.parametrize(
    ("required_evidence", "requires_external_verification"),
    [
        ([], False),
        (["order_context"], True),
        (["business_knowledge"], True),
        (["order_context", "business_knowledge"], True),
    ],
)
def test_required_evidence_represents_supported_routes(
    required_evidence: list[str],
    requires_external_verification: bool,
) -> None:
    """所需证据列表应能表达 direct、order、knowledge 和组合路径。"""

    payload = valid_finding_payload()
    payload["required_evidence"] = required_evidence
    payload["requires_external_verification"] = requires_external_verification

    finding = Finding.model_validate(payload)

    assert [item.value for item in finding.required_evidence] == required_evidence


def test_order_and_knowledge_evidence_are_parsed() -> None:
    """组合 Finding 应能把两类外部证据解析成对应模型。"""

    payload = valid_finding_payload()
    payload.update(
        {
            "requires_external_verification": True,
            "claim": "耳机购买十几天后是否可以退货。",
            "required_evidence": ["order_context", "business_knowledge"],
            "external_evidence": [
                {
                    "order_id": "order-001",
                    "field": "received_days",
                    "value": 12,
                    "queried_at": "2026-09-21T10:01:00+08:00",
                },
                {
                    "source_id": "after-sale-policy",
                    "chunk_id": "chunk-001",
                    "text": "符合条件的商品支持七天无理由退货。",
                    "metadata": {"version": "v1"},
                },
            ],
        }
    )

    finding = Finding.model_validate(payload)

    assert isinstance(finding.external_evidence[0], OrderEvidence)
    assert isinstance(finding.external_evidence[1], KnowledgeEvidence)
    assert finding.required_evidence == [
        RequiredEvidence.ORDER_CONTEXT,
        RequiredEvidence.BUSINESS_KNOWLEDGE,
    ]


@pytest.mark.parametrize(
    ("required_evidence", "requires_external_verification"),
    [
        ([], True),
        (["order_context"], False),
    ],
)
def test_external_verification_flag_must_match_required_evidence(
    required_evidence: list[str],
    requires_external_verification: bool,
) -> None:
    """是否需要外部核验必须与所需证据列表保持一致。"""

    payload = valid_finding_payload()
    payload["required_evidence"] = required_evidence
    payload["requires_external_verification"] = requires_external_verification

    with pytest.raises(ValidationError):
        Finding.model_validate(payload)


def test_empty_conversation_evidence_is_rejected() -> None:
    """Finding 必须至少有一条可追溯的会话证据。"""

    payload = valid_finding_payload()
    payload["conversation_evidence"] = []

    with pytest.raises(ValidationError):
        Finding.model_validate(payload)


def test_unknown_required_evidence_is_rejected() -> None:
    """当前只允许 Order Context 和 Business Knowledge 两类外部证据。"""

    payload = valid_finding_payload()
    payload["requires_external_verification"] = True
    payload["required_evidence"] = ["customer_profile"]

    with pytest.raises(ValidationError):
        Finding.model_validate(payload)
