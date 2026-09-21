"""会话证据的确定性校验。

输入和输出都很简单：调用方提供 Conversation 和一条会话证据，
函数返回是否通过，以及失败原因。
"""

from schemas.conversation import Conversation
from schemas.evidence import ConversationEvidence


def verify_conversation_evidence(
    conversation: Conversation,
    evidence: ConversationEvidence,
) -> tuple[bool, str | None]:
    """检查一条会话证据是否能在原始会话中找到。"""

    target_message = None

    # 按 message_id 查找被引用的消息。
    for message in conversation.messages:
        if message.message_id == evidence.message_id:
            target_message = message
            break

    if target_message is None:
        return False, "message_id not found"

    # 客服违规原话必须来自客服消息，不能引用客户自己的话。
    if target_message.role != "agent":
        return False, "evidence message must be from agent"

    # 原话必须真实出现在被引用消息的文本中。
    if evidence.quote not in target_message.text:
        return False, "quote not found in agent message"

    return True, None