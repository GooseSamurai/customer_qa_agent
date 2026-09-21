"""围绕原 Finding、Claim 和已有 Evidence 的受约束复判。"""

import json

from pydantic import ValidationError

from model.qa_model import InvalidModelOutput, ModelClient, parse_json_output
from schemas.evidence import ExternalEvidence
from schemas.finding import Finding


def build_grounded_prompt(
    finding: Finding,
    evidence: list[ExternalEvidence],
) -> str:
    """构造只允许基于原 Claim 和 Evidence 的复判 Prompt。"""

    finding_data = finding.model_dump(mode="json")
    evidence_data = [item.model_dump(mode="json") for item in evidence]

    return f"""你要对一条已有 Finding 进行受约束复判。

要求：
1. 只判断原 Finding 中的 claim 是否被已有 Evidence 支持。
2. 不得重新分析整段客服会话。
3. 不得引入原始 Finding 和 Evidence 中没有的事实。
4. 返回一条修正或确认后的 Finding。
5. external_evidence 必须保留输入中使用的证据。

Original Finding：
{json.dumps(finding_data, ensure_ascii=False, indent=2)}

Evidence：
{json.dumps(evidence_data, ensure_ascii=False, indent=2)}

只返回一条 Finding 的 JSON。
"""


class GroundedJudge:
    """使用模型客户端完成有依据复判。"""

    def __init__(self, client: ModelClient) -> None:
        self.client = client

    def judge(
        self,
        finding: Finding,
        evidence: list[ExternalEvidence],
    ) -> Finding:
        """根据原 Claim 和 Evidence 返回复判后的 Finding。"""

        prompt = build_grounded_prompt(finding, evidence)
        raw_output = self.client.generate(prompt)

        try:
            payload = parse_json_output(raw_output)
        except json.JSONDecodeError as exc:
            raise InvalidModelOutput("model output is not valid JSON") from exc

        try:
            return Finding.model_validate(payload)
        except ValidationError as exc:
            raise InvalidModelOutput("model output does not match finding schema") from exc