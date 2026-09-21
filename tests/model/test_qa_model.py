"""QA Model wrapper 测试。"""

import json

import pytest

from model.qa_model import InvalidModelOutput, QAModel, parse_json_output
from schemas.conversation import Conversation
from schemas.finding import Finding
from schemas.qa_rule import QARule
from tests.fixtures.cases import CASE_A, MOCK_RULES


class FakeModelClient:
    """返回预设文本，记录收到的 Prompt。"""

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompt = ""

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return self.response


def finding_payload() -> dict:
    """返回模型输出中的一条 Finding。"""

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


def test_valid_model_output_is_parsed() -> None:
    """合法 JSON 应转换成 Finding 列表。"""

    conversation = Conversation.model_validate(CASE_A["conversation"])
    rules = [QARule.model_validate(MOCK_RULES[0])]
    client = FakeModelClient(json.dumps({"findings": [finding_payload()]}))
    model = QAModel(client)

    findings = model.analyze(conversation, rules)

    assert len(findings) == 1
    assert isinstance(findings[0], Finding)
    assert "conv-case-a" in client.prompt


def test_markdown_json_code_block_is_parsed() -> None:
    """Markdown JSON 代码块应能被解析。"""

    payload = parse_json_output('```json\n{"findings": []}\n```')

    assert payload == {"findings": []}


def test_invalid_json_is_rejected() -> None:
    """模型返回非法 JSON 时，应抛出明确异常。"""

    conversation = Conversation.model_validate(CASE_A["conversation"])
    model = QAModel(FakeModelClient("not json"))

    with pytest.raises(InvalidModelOutput):
        model.analyze(conversation, [])


def test_invalid_finding_schema_is_rejected() -> None:
    """JSON 合法但不符合 Finding Schema 时，应抛出明确异常。"""

    conversation = Conversation.model_validate(CASE_A["conversation"])
    client = FakeModelClient(json.dumps({"findings": [{"rule_id": "incomplete"}]}))
    model = QAModel(client)

    with pytest.raises(InvalidModelOutput):
        model.analyze(conversation, [])