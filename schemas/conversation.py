"""标准化客服会话的数据契约。

Schema 在本项目中表示“系统允许接收和传递的数据形状与规则”。
它不负责质检判断，也不调用模型、数据库、RAG 或 Agent。

Pydantic 的职责是把调用方传入的原始数据（通常是 JSON/dict）解析成
受约束的 Python 对象；如果数据不符合声明，就统一抛出 ValidationError。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Literal 用来限制字符串的精确取值集合。
# 当前企业标准化输入只定义客户和客服两种角色。
# 如果未来需要 system 消息，应作为公共 Schema 变更单独评估，
# 而不是在业务代码中临时接受额外角色。
MessageRole = Literal["customer", "agent"]


class Message(BaseModel):
    """企业标准化会话中的一条消息。

    继承 BaseModel 后，下面的类属性会被 Pydantic 当作字段声明。
    创建对象时，Pydantic 会检查字段是否存在、类型是否可转换，
    并负责序列化与反序列化。
    """

    # 企业侧消息唯一标识。Conversation 会用它关联 Evidence。
    message_id: str

    # 角色必须满足 MessageRole 的限制。
    role: MessageRole

    # 输入可使用 ISO 8601 时间字符串；
    # Pydantic 会把通过校验的值转换成 Python datetime 对象。
    timestamp: datetime

    # 消息原文。T002 没有要求检查空字符串，因此这里只约束为 str，
    # 暂不增加未被验收条件要求的额外规则。
    text: str


class Conversation(BaseModel):
    """一次完整的标准化客服会话。

    Conversation 与 Message 是嵌套关系：
    一个 Conversation 包含一个 list[Message]。
    """

    # 会话级标识和参与方标识，用于后续审计、检索和追踪。
    conversation_id: str
    channel: str
    customer_id: str
    agent_id: str

    # 企业会话可能关联 0 个或多个订单，因此使用列表而不是单个字符串。
    order_ids: list[str]

    # 会话开始时间；Pydantic 同样会把 ISO 8601 字符串转换成 datetime。
    start_time: datetime

    # list[Message] 不只是给静态类型检查器看的注解。
    # Pydantic 会依据它把 messages 中的嵌套 dict 自动转换成 Message 对象。
    # Field(min_length=1) 表示该列表至少包含一条消息。
    messages: list[Message] = Field(min_length=1)

    # model_validator 用于检查“多个字段或列表元素之间”的关系。
    # mode="after" 表示先完成 Message 的字段解析，再执行这里的跨元素检查；
    # 此时每个元素已经是可以直接读取 .message_id 的 Message 对象。
    @model_validator(mode="after")
    def validate_unique_message_ids(self) -> "Conversation":
        """保证同一会话内的 message_id 不重复。"""

        # 提取所有 message_id。
        message_ids = [message.message_id for message in self.messages]

        # set 会自动去重：如果去重后的数量变少，就说明存在重复 ID。
        # 抛出 ValueError 后，Pydantic 会把它整理成统一的 ValidationError。
        if len(message_ids) != len(set(message_ids)):
            raise ValueError("message_id must be unique within a conversation")

        # after validator 必须返回校验后的模型自身，供 Pydantic 继续使用。
        return self