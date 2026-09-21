"""质检模型的结构化输出契约。"""

from pydantic import BaseModel

from schemas.finding import Finding


class QAModelOutput(BaseModel):
    """模型必须返回的顶层结构。"""

    # 允许为空列表，因为一段会话不一定存在问题。
    findings: list[Finding]