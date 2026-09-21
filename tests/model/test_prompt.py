"""Prompt 和结构化输出契约测试。"""

from model.output_schema import QAModelOutput
from model.prompt import build_qa_prompt
from schemas.conversation import Conversation
from schemas.finding import Finding
from schemas.qa_rule import QARule
from tests.fixtures.cases import CASE_A, MOCK_RULES


def sample_finding_payload() -> dict:
    """返回一条纯语义 Finding。"""

    return {
        "rule_id": "rule-blame",
        "risk_type": "blame_shifting",
        "severity": "high",
        "reason": "客服将客户问题直接推给物流方。",
        "conversation_evidence": [
            {"message_id": "msg-a-002", "quote": "这个不归我们管"}
        ],
        "requires_external_verification": False,
        "claim": None,
        "required_evidence": [],
        "external_evidence": [],
    }


def test_prompt_contains_conversation_and_enabled_rules() -> None:
    """Prompt 应包含会话和启用规则，并排除停用规则。"""

    conversation = Conversation.model_validate(CASE_A["conversation"])
    enabled_rule = QARule.model_validate(MOCK_RULES[0])
    disabled_rule = enabled_rule.model_copy(
        update={"rule_id": "rule-disabled", "enabled": False}
    )

    prompt = build_qa_prompt(conversation, [enabled_rule, disabled_rule])

    assert "conv-case-a" in prompt
    assert "这个不归我们管" in prompt
    assert "rule-blame" in prompt
    assert "rule-disabled" not in prompt


def test_output_schema_uses_finding() -> None:
    """模型输出的 findings 必须解析成现有 Finding 对象。"""

    output = QAModelOutput.model_validate({"findings": [sample_finding_payload()]})

    assert isinstance(output.findings[0], Finding)
    assert output.findings[0].rule_id == "rule-blame"