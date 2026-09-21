"""vLLM HTTP 客户端测试，不要求真实服务常驻。"""

import httpx
import pytest

from serving.vllm_client import VLLMClient, VLLMServiceError


class FakeResponse:
    """模拟 httpx.Response 需要的最小接口。"""

    def __init__(self, payload=None, error=None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


def test_vllm_client_returns_message_content(monkeypatch) -> None:
    """客户端应返回 choices[0].message.content。"""

    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            {"choices": [{"message": {"content": "OK"}}]}
        )

    monkeypatch.setattr("serving.vllm_client.httpx.post", fake_post)
    client = VLLMClient("http://localhost:8000", "qwen-adapter", timeout=12)

    result = client.generate("hello")

    assert result == "OK"
    assert captured["url"] == "http://localhost:8000/v1/chat/completions"
    assert captured["json"]["model"] == "qwen-adapter"
    assert captured["timeout"] == 12


def test_vllm_timeout_raises_service_error(monkeypatch) -> None:
    """网络超时应转换成统一的 VLLMServiceError。"""

    request = httpx.Request("POST", "http://localhost:8000")

    def fake_post(*args, **kwargs):
        raise httpx.TimeoutException("timeout", request=request)

    monkeypatch.setattr("serving.vllm_client.httpx.post", fake_post)
    client = VLLMClient("http://localhost:8000", "qwen-adapter")

    with pytest.raises(VLLMServiceError):
        client.generate("hello")


def test_invalid_response_raises_service_error(monkeypatch) -> None:
    """缺少 choices 的响应应被明确拒绝。"""

    monkeypatch.setattr(
        "serving.vllm_client.httpx.post",
        lambda *args, **kwargs: FakeResponse({"choices": []}),
    )
    client = VLLMClient("http://localhost:8000", "qwen-adapter")

    with pytest.raises(VLLMServiceError):
        client.generate("hello")