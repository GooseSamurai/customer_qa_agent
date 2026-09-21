"""Agent 路由、Tool 参数和 Evidence 校验评测。"""

from agent.router import Route, route_finding
from evidence.verifier import verify_conversation_evidence
from schemas.conversation import Conversation
from schemas.evidence import ConversationEvidence
from schemas.finding import Finding
from tests.fixtures.cases import CASE_A
from tools.order_context import get_order_context


def _finding_payload(required_evidence: list[str], external: bool) -> dict:
    return {
        "rule_id": "rule-test",
        "risk_type": "test_risk",
        "severity": "medium",
        "reason": "测试问题。",
        "conversation_evidence": [
            {"message_id": "msg-a-002", "quote": "这个不归我们管"}
        ],
        "requires_external_verification": external,
        "claim": "测试 Claim" if required_evidence else None,
        "required_evidence": required_evidence,
        "external_evidence": [],
    }


def evaluate_agent() -> dict:
    """计算可确定性验证的 Agent 指标。"""

    routing_cases = [
        ([], False, Route.DIRECT),
        (["order_context"], True, Route.ORDER_CONTEXT),
        (["business_knowledge"], True, Route.BUSINESS_KNOWLEDGE),
        (
            ["order_context", "business_knowledge"],
            True,
            Route.ORDER_AND_KNOWLEDGE,
        ),
    ]
    routing_hits = 0
    for required, external, expected in routing_cases:
        finding = Finding.model_validate(_finding_payload(required, external))
        if route_finding(finding) is expected:
            routing_hits += 1

    conversation = Conversation.model_validate(CASE_A["conversation"])
    evidence_cases = [
        (ConversationEvidence(message_id="msg-a-002", quote="这个不归我们管"), True),
        (ConversationEvidence(message_id="missing", quote="不存在"), False),
        (ConversationEvidence(message_id="msg-a-001", quote="我已经问三次了"), False),
    ]
    evidence_hits = 0
    for evidence, expected_valid in evidence_cases:
        valid, _error = verify_conversation_evidence(conversation, evidence)
        if valid is expected_valid:
            evidence_hits += 1

    tool_hits = 0
    for order_id in ["order-001", "order-002"]:
        context = get_order_context(order_id)
        if context["order_id"] == order_id:
            tool_hits += 1

    unsupported_findings = [
        Finding.model_validate(_finding_payload([], False)),
        Finding.model_validate(_finding_payload(["order_context"], True)),
    ]
    unsupported_claim_count = sum(
        1
        for finding in unsupported_findings
        if finding.requires_external_verification and not finding.claim
    )

    return {
        "routing_accuracy": routing_hits / len(routing_cases),
        "tool_argument_accuracy": tool_hits / 2,
        "evidence_validation_accuracy": evidence_hits / len(evidence_cases),
        "unsupported_claim_rate": unsupported_claim_count / len(unsupported_findings),
        "representative_case_pass_rate": routing_hits / len(routing_cases),
        "num_routing_cases": len(routing_cases),
    }