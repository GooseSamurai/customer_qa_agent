"""Finding 路由测试。"""

import pytest

from agent.router import Route, route_finding
from schemas.finding import Finding


def finding_payload(
    required_evidence: list[str],
    requires_external_verification: bool,
) -> dict:
    """返回测试用 Finding 输入。"""

    return {
        "rule_id": "rule-test",
        "risk_type": "test_risk",
        "severity": "medium",
        "reason": "测试问题。",
        "conversation_evidence": [
            {"message_id": "msg-001", "quote": "测试原话"}
        ],
        "requires_external_verification": requires_external_verification,
        "claim": "测试 Claim" if required_evidence else None,
        "required_evidence": required_evidence,
        "external_evidence": [],
    }


@pytest.mark.parametrize(
    ("required_evidence", "requires_external_verification", "expected_route"),
    [
        ([], False, Route.DIRECT),
        (["order_context"], True, Route.ORDER_CONTEXT),
        (["business_knowledge"], True, Route.BUSINESS_KNOWLEDGE),
        (
            ["order_context", "business_knowledge"],
            True,
            Route.ORDER_AND_KNOWLEDGE,
        ),
    ],
)
def test_known_routes(
    required_evidence: list[str],
    requires_external_verification: bool,
    expected_route: Route,
) -> None:
    """已知证据组合应返回对应路径。"""

    finding = Finding.model_validate(
        finding_payload(required_evidence, requires_external_verification)
    )

    assert route_finding(finding) is expected_route


def test_unknown_required_evidence_goes_to_human_review() -> None:
    """未知证据类型不猜测，统一转人工复核。"""

    finding = Finding.model_construct(
        rule_id="rule-test",
        risk_type="test_risk",
        severity="medium",
        reason="测试问题。",
        conversation_evidence=[],
        requires_external_verification=True,
        claim="测试 Claim",
        required_evidence=["unknown_source"],
        external_evidence=[],
    )

    assert route_finding(finding) is Route.HUMAN_REVIEW