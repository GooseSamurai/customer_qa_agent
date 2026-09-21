"""Conversation Schema 的正常与异常输入测试。

测试关注两件事：
1. 合法输入能否被 Pydantic 解析成预期的 Python 对象；
2. 非法输入是否稳定地转换成 ValidationError。
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from schemas.conversation import Conversation, Message


def valid_conversation_payload() -> dict:
    """返回一个通过 Schema 校验的最小会话输入。

    这里刻意使用原始 dict 和时间字符串，模拟 API 收到 JSON 后的数据形态，
    而不是直接构造 Python 对象，这样测试才覆盖 Pydantic 的解析过程。
    """

    return {
        "conversation_id": "conv-001",
        "channel": "web",
        "customer_id": "customer-001",
        "agent_id": "agent-001",
        "order_ids": [],
        "start_time": "2026-09-21T10:00:00+08:00",
        "messages": [
            {
                "message_id": "msg-001",
                "role": "customer",
                "timestamp": "2026-09-21T10:00:00+08:00",
                "text": "请问退款什么时候到账？",
            },
            {
                "message_id": "msg-002",
                "role": "agent",
                "timestamp": "2026-09-21T10:00:10+08:00",
                "text": "我帮您查询一下。",
            },
        ],
    }


def test_valid_conversation_is_parsed() -> None:
    """正常输入应生成嵌套 Message，并把时间字符串解析为 datetime。"""

    # model_validate() 是 Pydantic 的入口：
    # dict -> 字段检查/类型转换 -> 嵌套 Message 构造 -> after validator。
    conversation = Conversation.model_validate(valid_conversation_payload())

    # 以下断言证明返回的不只是普通 dict，而是包含嵌套模型对象的 Conversation。
    assert conversation.messages[0].role == "customer"
    assert isinstance(conversation.messages[0], Message)
    assert isinstance(conversation.start_time, datetime)


def test_invalid_role_is_rejected() -> None:
    """未定义的角色不能被 Schema 接受。"""

    payload = valid_conversation_payload()

    # system 不在 Literal["customer", "agent"] 中，Pydantic 应拒绝该输入。
    payload["messages"][0]["role"] = "system"

    # pytest.raises 断言代码一定会抛出 ValidationError；
    # 如果代码没有抛异常，测试会失败。
    with pytest.raises(ValidationError):
        Conversation.model_validate(payload)


def test_empty_messages_are_rejected() -> None:
    """会话必须至少包含一条消息。"""

    payload = valid_conversation_payload()
    payload["messages"] = []

    # 这里触发的是 Field(min_length=1)，而不是自定义 validator。
    with pytest.raises(ValidationError):
        Conversation.model_validate(payload)


def test_duplicate_message_ids_are_rejected() -> None:
    """同一会话中的 message_id 必须唯一。"""

    payload = valid_conversation_payload()

    # 人为把第二条消息的 ID 改成与第一条相同。
    payload["messages"][1]["message_id"] = payload["messages"][0]["message_id"]

    # 这里触发 model_validator，并由它抛出 ValueError，
    # Pydantic 再统一包装为 ValidationError。
    with pytest.raises(ValidationError):
        Conversation.model_validate(payload)