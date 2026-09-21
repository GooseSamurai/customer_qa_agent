"""使用真实 CrossEncoder 对候选知识片段重排。"""

import os
from pathlib import Path

# 模型已经提前下载，运行时禁止继续访问 Hugging Face。
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from huggingface_hub import try_to_load_from_cache
from sentence_transformers import CrossEncoder

from rag.ingest import KnowledgeChunk

RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"
_reranker = None


def get_local_model_path(model_name: str) -> str:
    """从 Hugging Face 缓存中找到已经下载的模型目录。"""

    config_path = try_to_load_from_cache(model_name, "config.json")
    if not isinstance(config_path, str):
        raise FileNotFoundError(f"local model cache not found: {model_name}")

    return str(Path(config_path).parent)


def get_reranker() -> CrossEncoder:
    """只加载一次 BGE 重排模型。"""

    global _reranker

    if _reranker is None:
        _reranker = CrossEncoder(
            get_local_model_path(RERANKER_MODEL_NAME),
            local_files_only=True,
        )

    return _reranker


def rerank(
    query: str,
    candidates: list[tuple[KnowledgeChunk, float]],
) -> list[tuple[KnowledgeChunk, float]]:
    """使用 CrossEncoder 对候选片段重新排序。"""

    if not candidates:
        return []

    pairs = [(query, chunk.text) for chunk, _score in candidates]
    scores = get_reranker().predict(pairs)

    ranked = sorted(
        zip((chunk for chunk, _score in candidates), scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    return [(chunk, float(score)) for chunk, score in ranked]