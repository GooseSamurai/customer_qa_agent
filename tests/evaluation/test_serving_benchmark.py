"""Serving benchmark 结构测试。"""

from evaluation import serving_benchmark


class FakeClient:
    def __init__(self, **kwargs) -> None:
        pass

    def generate(self, prompt: str) -> str:
        return "OK"


def test_benchmark_returns_latency_and_throughput(monkeypatch) -> None:
    monkeypatch.setattr(serving_benchmark, "LocalQwenClient", FakeClient)
    monkeypatch.setattr(serving_benchmark.torch.cuda, "is_available", lambda: False)

    report = serving_benchmark.benchmark_local_qwen(repeat=2)

    assert report["requests"] == 2
    assert report["latency_seconds_per_request"] >= 0
    assert report["serial_requests_per_second"] > 0