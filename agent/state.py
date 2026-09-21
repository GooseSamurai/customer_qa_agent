"""Agent 工作流节点之间共享的状态。"""

from typing import TypedDict

from agent.router import Route
from schemas.conversation import Conversation
from schemas.evidence import KnowledgeEvidence, OrderEvidence
from schemas.finding import Finding


class AgentState(TypedDict, total=False):
    """单个 Finding 在一次工作流中的状态。"""

    conversation: Conversation
    finding: Finding
    route: Route
    order_evidence: list[OrderEvidence]
    knowledge_evidence: list[KnowledgeEvidence]
    final_finding: Finding | None
    status: str
    error: str | None