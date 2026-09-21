"""质检模型 Prompt 的简单构造逻辑。"""

import json

from schemas.conversation import Conversation
from schemas.qa_rule import QARule


def build_qa_prompt(conversation: Conversation, rules: list[QARule]) -> str:
    """把会话和启用规则转换成模型可读的 Prompt。"""

    enabled_rules = [rule.model_dump(mode="json") for rule in rules if rule.enabled]
    example_rule_id = enabled_rules[0]["rule_id"] if enabled_rules else "rule-id"
    conversation_data = conversation.model_dump(mode="json")

    output_example = {
        "findings": [
            {
                "rule_id": example_rule_id,
                "risk_type": "blame_shifting",
                "severity": "high",
                "reason": "客服将客户问题直接推给物流方。",
                "conversation_evidence": [
                    {"message_id": "msg-002", "quote": "不归我们管"}
                ],
                "requires_external_verification": False,
                "claim": None,
                "required_evidence": [],
                "external_evidence": [],
            }
        ]
    }

    return f"""你是电商客服质检模型。

请根据 Conversation 和启用的 QARule 找出所有独立问题。

要求：
1. 一段会话可以输出 0 条或多条 Finding。
2. 每条 Finding 必须引用真实的 message_id 和原文 quote。
3. 纯语义问题不需要外部证据；需要核验业务事实时填写 claim 和 required_evidence。
4. required_evidence 只能使用 order_context 或 business_knowledge。
5. rule_id 必须使用输入 QARule 中的真实 rule_id，不能复制示例值。
6. 不要根据知识文档自由回答，只输出结构化 Finding。
7. external_evidence 在质检模型阶段必须为空列表。

Conversation：
{json.dumps(conversation_data, ensure_ascii=False, indent=2)}

QARule：
{json.dumps(enabled_rules, ensure_ascii=False, indent=2)}

只返回如下 JSON 结构：
{json.dumps(output_example, ensure_ascii=False, indent=2)}
"""