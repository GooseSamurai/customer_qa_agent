"""会话证据校验的正常和异常测试。"""

from evidence.verifier import verify_conversation_evidence
from schemas.conversation import Conversation
from schemas.evidence import ConversationEvidence
from tests.fixtures.cases import CASE_A


def case_a_conversation() -> Conversation:
    """把 Case A 的原始字典转成 Conversation 对象。"""

    return Conversation.model_validate(CASE_A["conversation"])


def test_valid_agent_evidence_is_accepted() -> None:
    """客服消息中存在原话时，证据应通过。"""

    conversation = case_a_conversation()
    evidence = ConversationEvidence(
        message_id="msg-a-002",
        quote="这个不归我们管",
    )

    valid, error = verify_conversation_evidence(conversation, evidence)

    assert valid is True
    assert error is None


def test_missing_message_id_is_rejected() -> None:
    """引用的消息编号不存在时，应返回明确错误。"""

    conversation = case_a_conversation()
    evidence = ConversationEvidence(message_id="missing", quote="随便一段话")

    valid, error = verify_conversation_evidence(conversation, evidence)

    assert valid is False
    assert error == "message_id not found"


def test_customer_message_cannot_be_used_as_agent_evidence() -> None:
    """客户自己的消息不能作为客服违规原话。"""

    conversation = case_a_conversation()
    evidence = ConversationEvidence(
        message_id="msg-a-001",
        quote="我已经问三次了",
    )

    valid, error = verify_conversation_evidence(conversation, evidence)

    assert valid is False
    assert error == "evidence message must be from agent"


def test_quote_must_exist_in_message() -> None:
    """原话不存在于指定客服消息时，应返回明确错误。"""

    conversation = case_a_conversation()
    evidence = ConversationEvidence(
        message_id="msg-a-002",
        quote="这句话不存在",
    )

    valid, error = verify_conversation_evidence(conversation, evidence)

    assert valid is False
    assert error == "quote not found in agent message"