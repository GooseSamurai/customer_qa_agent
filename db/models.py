"""持久化层使用的最小数据对象。"""

from enum import Enum
from typing import Any

from pydantic import BaseModel

from schemas.finding import Finding


class ReviewDecision(str, Enum):
    """人工复核结果。"""

    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    CORRECTION = "correction"


class ReviewRecord(BaseModel):
    """一次人工复核记录。"""

    review_id: str
    finding_id: str
    decision: ReviewDecision
    corrected_finding: Finding | None = None


class AgentRunRecord(BaseModel):
    """一次 Agent 工作流运行的摘要。"""

    run_id: str
    case_id: str
    status: str
    state: dict[str, Any]