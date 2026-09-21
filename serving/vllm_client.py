"""vLLM OpenAI 兼容接口的最小 HTTP 客户端。"""

import httpx


class VLLMServiceError(RuntimeError):
    """调用 vLLM 服务失败时使用的统一异常。"""


class VLLMClient:
    """把 HTTP 细节封装在 generate(prompt) 后面。"""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout: float = 60.0,
        max_tokens: int = 1024,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(self, prompt: str) -> str:
        """调用 vLLM Chat Completions 并返回文本。"""

        try:
            response = httpx.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": self.max_tokens,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise VLLMServiceError("vLLM request timed out") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise VLLMServiceError("vLLM returned an invalid response") from exc