"""Finding 使用的可追溯证据数据契约。

本文件只定义证据数据的形状。它不判断 quote 是否真实存在，
也不负责调用订单接口或 RAG。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationEvidence(BaseModel):
    """来自客服会话原文的一条证据。"""

    # message_id 用于定位原始消息，quote 用于后续做程序化存在性校验。
    message_id: str
    quote: str


class OrderEvidence(BaseModel):
    """来自订单上下文的一条结构化事实。"""

    order_id: str
    field: str

    # 业务字段值可能是字符串、数字、布尔值、空值或嵌套结构，
    # T004 只负责承载，不在 Schema 中解释具体业务含义。
    value: Any

    queried_at: datetime


class KnowledgeEvidence(BaseModel):
    """来自业务知识检索的一条文档片段。"""

    source_id: str
    chunk_id: str
    text: str

    # RAG 返回的版本、生效时间等元数据由后续模块写入并校验。
    metadata: dict[str, Any] = Field(default_factory=dict)


ExternalEvidence = OrderEvidence | KnowledgeEvidence
