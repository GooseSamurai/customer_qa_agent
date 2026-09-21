"""单 Finding Agent workflow 的集成测试。"""

from datetime import date

from agent.router import Route
from agent.workflow import run_workflow
from schemas.conversation import Conversation
from schemas.evidence import KnowledgeEvidence
from schemas.finding import Finding
from tests.fixtures.cases import CASE_A, CASE_B, CASE_C


class FakeJudge:
    """返回带外部证据的原 Finding，不调用真实模型。"""

    def judge(self, finding: Finding, evidence: list) -> Finding:
        return finding.model_copy(update={"external_evidence": evidence})


def make_finding(
    required_evidence: list[str],
    requires_external_verification: bool,
    message_id: str,
    quote: str,
) -> Finding:
    """构造测试用 Finding。"""

    return Finding.model_validate(
        {
            "rule_id": "rule-test",
            "risk_type": "test_risk",
            "severity": "medium",
            "reason": "测试问题。",
            "conversation_evidence": [
                {"message_id": message_id, "quote": quote}
            ],
            "requires_external_verification": requires_external_verification,
            "claim": "测试 Claim" if required_evidence else None,
            "required_evidence": required_evidence,
            "external_evidence": [],
        }
    )


def test_direct_path_completes() -> None:
    """纯语义 Finding 应直接完成，不调用工具。"""

    conversation = Conversation.model_validate(CASE_A["conversation"])
    finding = make_finding([], False, "msg-a-002", "这个不归我们管")

    results = run_workflow(conversation, [finding], FakeJudge(), [])

    assert results[0]["status"] == "completed"
    assert results[0]["route"] is Route.DIRECT
    assert results[0]["final_finding"] == finding


def test_order_path_completes() -> None:
    """订单路径应获取订单证据并进入复判。"""

    conversation = Conversation.model_validate(CASE_C["conversation"])
    finding = make_finding(
        ["order_context"],
        True,
        "msg-c-002",
        "今晚肯定到账",
    )

    results = run_workflow(conversation, [finding], FakeJudge(), [])

    assert results[0]["status"] == "completed"
    assert results[0]["route"] is Route.ORDER_CONTEXT
    assert results[0]["order_evidence"]


def test_knowledge_path_completes(monkeypatch) -> None:
    """知识路径应获取 KnowledgeEvidence 并进入复判。"""

    conversation = Conversation.model_validate(CASE_B["conversation"])
    finding = make_finding(
        ["business_knowledge"],
        True,
        "msg-b-002",
        "超过 7 天都不能退",
    )
    knowledge = KnowledgeEvidence(
        source_id="return_exchange_policy",
        chunk_id="return_exchange_policy-chunk-1",
        text="客户自签收商品次日起 7 天内可以申请无理由退货。",
        metadata={"category": "after_sale"},
    )
    monkeypatch.setattr(
        "agent.workflow.search_knowledge",
        lambda *args, **kwargs: [knowledge],
    )

    results = run_workflow(conversation, [finding], FakeJudge(), [])

    assert results[0]["status"] == "completed"
    assert results[0]["route"] is Route.BUSINESS_KNOWLEDGE
    assert results[0]["knowledge_evidence"] == [knowledge]


def test_combined_path_completes(monkeypatch) -> None:
    """组合路径应同时获取订单和知识证据。"""

    conversation = Conversation.model_validate(CASE_B["conversation"])
    finding = make_finding(
        ["order_context", "business_knowledge"],
        True,
        "msg-b-002",
        "超过 7 天都不能退",
    )
    knowledge = KnowledgeEvidence(
        source_id="return_exchange_policy",
        chunk_id="return_exchange_policy-chunk-2",
        text="质量问题退货的处理方式以审核结果为准。",
        metadata={"category": "after_sale"},
    )
    monkeypatch.setattr(
        "agent.workflow.search_knowledge",
        lambda *args, **kwargs: [knowledge],
    )

    results = run_workflow(conversation, [finding], FakeJudge(), [])

    assert results[0]["status"] == "completed"
    assert results[0]["route"] is Route.ORDER_AND_KNOWLEDGE
    assert results[0]["order_evidence"]
    assert results[0]["knowledge_evidence"] == [knowledge]


def test_order_failure_goes_to_human_review() -> None:
    """订单查询失败时应进入人工复核。"""

    conversation_data = CASE_C["conversation"].copy()
    conversation_data["order_ids"] = ["missing-order"]
    conversation = Conversation.model_validate(conversation_data)
    finding = make_finding(
        ["order_context"],
        True,
        "msg-c-002",
        "今晚肯定到账",
    )

    results = run_workflow(conversation, [finding], FakeJudge(), [])

    assert results[0]["status"] == "human_review"
    assert results[0]["error"] == "order not found: missing-order"


def test_invalid_conversation_evidence_goes_to_human_review() -> None:
    """会话证据不存在时应进入人工复核。"""

    conversation = Conversation.model_validate(CASE_A["conversation"])
    finding = make_finding([], False, "missing-message", "不存在的原话")

    results = run_workflow(conversation, [finding], FakeJudge(), [])

    assert results[0]["status"] == "human_review"
    assert results[0]["error"] == "message_id not found"