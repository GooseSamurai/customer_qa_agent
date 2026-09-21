"""Finding 粒度的处理路径判断。"""

from enum import Enum

from schemas.finding import Finding, RequiredEvidence


class Route(str, Enum):
    """单个 Finding 需要走的处理路径。"""

    DIRECT = "direct"
    ORDER_CONTEXT = "order_context"
    BUSINESS_KNOWLEDGE = "business_knowledge"
    ORDER_AND_KNOWLEDGE = "order_and_knowledge"
    HUMAN_REVIEW = "human_review"


def route_finding(finding: Finding) -> Route:
    """根据 Finding 的 required_evidence 返回处理路径。"""

    required = set(finding.required_evidence)

    if not finding.requires_external_verification and not required:
        return Route.DIRECT

    if required == {RequiredEvidence.ORDER_CONTEXT}:
        return Route.ORDER_CONTEXT

    if required == {RequiredEvidence.BUSINESS_KNOWLEDGE}:
        return Route.BUSINESS_KNOWLEDGE

    if required == {
        RequiredEvidence.ORDER_CONTEXT,
        RequiredEvidence.BUSINESS_KNOWLEDGE,
    }:
        return Route.ORDER_AND_KNOWLEDGE

    # 没有匹配到已知组合时，不猜测用户意图。
    return Route.HUMAN_REVIEW