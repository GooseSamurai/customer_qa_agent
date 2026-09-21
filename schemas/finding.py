"""质检 Finding 的数据契约。

Finding 是系统处理外部事实核验、证据校验和人工复核的核心单位。
本文件只定义数据形状，不实现 Router，也不决定调用哪个 Tool。
"""

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from schemas.evidence import ConversationEvidence, ExternalEvidence
from schemas.qa_rule import RuleSeverity


class RequiredEvidence(str, Enum):
    """外部核验所需的证据类型。"""

    ORDER_CONTEXT = "order_context"
    BUSINESS_KNOWLEDGE = "business_knowledge"


class Finding(BaseModel):
    """一条独立的质检发现。"""

    rule_id: str
    risk_type: str
    severity: RuleSeverity
    reason: str

    # 没有会话原文支撑的 Finding 无法追溯，因此至少保留一条会话证据。
    conversation_evidence: list[ConversationEvidence] = Field(min_length=1)

    # 是否进入外部取证流程。
    requires_external_verification: bool

    # 纯语义问题可以为空；需要核验具体事实时填写待核验 Claim。
    claim: str | None = None

    # 空列表表示 direct；其余组合表示 order、knowledge 或 order+knowledge。
    required_evidence: list[RequiredEvidence]

    # 外部证据由后续 Tool/RAG 流程补充，Finding 初始输出时可以为空。
    external_evidence: list[ExternalEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_external_verification_consistency(self) -> "Finding":
        """保证“是否需要外部核验”和所需证据列表表达一致。"""

        if self.requires_external_verification != bool(self.required_evidence):
            raise ValueError(
                "requires_external_verification must match required_evidence"
            )

        return self
