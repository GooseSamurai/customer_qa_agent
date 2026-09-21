"""本地模型服务的简单延迟和显存基准。"""

import time

import torch

from serving.local_qwen import LocalQwenClient


def benchmark_local_qwen(
    prompt: str = "只回复：OK",
    repeat: int = 2,
    max_new_tokens: int = 8,
) -> dict:
    """执行串行小样本基准，不伪造并发吞吐。"""

    client = LocalQwenClient(max_new_tokens=max_new_tokens)

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    start = time.perf_counter()
    for _ in range(repeat):
        client.generate(prompt)
    elapsed = time.perf_counter() - start

    return {
        "requests": repeat,
        "elapsed_seconds": elapsed,
        "latency_seconds_per_request": elapsed / repeat,
        "serial_requests_per_second": repeat / elapsed if elapsed else 0.0,
        "gpu_memory_mb": (
            torch.cuda.max_memory_allocated() / (1024 * 1024)
            if torch.cuda.is_available()
            else 0.0
        ),
    }


if __name__ == "__main__":
    print(benchmark_local_qwen())