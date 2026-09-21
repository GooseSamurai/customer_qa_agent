"""与具体模型供应商解耦的质检模型封装。"""

import json
from typing import Protocol

from pydantic import ValidationError

from model.output_schema import QAModelOutput
from model.prompt import build_qa_prompt
from schemas.conversation import Conversation
from schemas.finding import Finding
from schemas.qa_rule import QARule


class ModelClient(Protocol):
    """只要求模型客户端把 Prompt 转成字符串。"""

    def generate(self, prompt: str) -> str:
        """返回模型生成的原始文本。"""


class InvalidModelOutput(ValueError):
    """模型返回的不是合法 JSON 或不符合 Finding Schema。"""


def parse_json_output(raw_output: str) -> dict:
    """去掉 Instruct 模型常见的 Markdown JSON 包装后解析。"""

    text = raw_output.strip()

    if text.startswith("```"):
        first_line_end = text.find("\n")
        if first_line_end >= 0:
            text = text[first_line_end + 1:]
        if text.endswith("```"):
            text = text[:-3].strip()

    return json.loads(text)


class QAModel:
    """质检模型业务封装。"""

    def __init__(self, client: ModelClient) -> None:
        self.client = client

    def analyze(
        self,
        conversation: Conversation,
        rules: list[QARule],
    ) -> list[Finding]:
        """调用模型，并返回结构化 Finding 列表。"""

        prompt = build_qa_prompt(conversation, rules)
        raw_output = self.client.generate(prompt)

        try:
            payload = parse_json_output(raw_output)
        except json.JSONDecodeError as exc:
            raise InvalidModelOutput("model output is not valid JSON") from exc

        try:
            output = QAModelOutput.model_validate(payload)
        except ValidationError as exc:
            raise InvalidModelOutput("model output does not match finding schema") from exc

        return output.findings