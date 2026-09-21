"""业务层使用的模型服务适配器。"""

from model.qa_model import QAModel
from serving.vllm_client import VLLMClient


class VLLMService:
    """把 vLLM 客户端适配成 QA Model 依赖。"""

    def __init__(self, client: VLLMClient) -> None:
        self.client = client

    def generate(self, prompt: str) -> str:
        return self.client.generate(prompt)

    def create_qa_model(self) -> QAModel:
        return QAModel(self)