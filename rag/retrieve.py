"""基于真实中文 Embedding 和 Chroma 的知识召回。"""

import os
from datetime import date
from pathlib import Path

# 模型已经提前下载，运行时禁止继续访问 Hugging Face。
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from huggingface_hub import try_to_load_from_cache
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from rag.ingest import KnowledgeChunk

EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
_embeddings = None


def get_local_model_path(model_name: str) -> str:
    """从 Hugging Face 缓存中找到已经下载的模型目录。"""

    config_path = try_to_load_from_cache(model_name, "config.json")
    if not isinstance(config_path, str):
        raise FileNotFoundError(f"local model cache not found: {model_name}")

    return str(Path(config_path).parent)


def get_embeddings() -> HuggingFaceEmbeddings:
    """只加载一次 BGE 中文向量模型。"""

    global _embeddings

    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model=get_local_model_path(EMBEDDING_MODEL_NAME),
            model_kwargs={"local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )

    return _embeddings


def chunk_to_document(chunk: KnowledgeChunk) -> Document:
    """把知识片段转换成 Chroma 可保存的文档。"""

    metadata = {
        "source_id": chunk.source_id,
        "chunk_id": chunk.chunk_id,
        "section": chunk.section,
    }
    metadata.update(
        {
            key: value
            for key, value in chunk.metadata.model_dump(mode="json").items()
            if value is not None
        }
    )
    return Document(page_content=chunk.text, metadata=metadata)


def build_chroma_filter(filters: dict[str, object] | None) -> dict | None:
    """把普通过滤字典转换成 Chroma 接受的 where 格式。"""

    if not filters:
        return None

    if len(filters) == 1:
        return dict(filters)

    return {"$and": [{key: value} for key, value in filters.items()]}


def retrieve(
    query: str,
    chunks: list[KnowledgeChunk],
    filters: dict[str, object] | None = None,
    top_k: int = 3,
    as_of: date | None = None,
) -> list[tuple[KnowledgeChunk, float]]:
    """生成向量、写入 Chroma，并返回 TopK 知识片段。"""

    if not chunks:
        return []

    documents = [chunk_to_document(chunk) for chunk in chunks]
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        ids=[chunk.chunk_id for chunk in chunks],
    )

    # as_of 存在时需要检查所有候选的失效日期，因此先召回全部片段。
    candidate_count = len(chunks) if as_of is not None else min(top_k, len(chunks))
    results = vector_store.similarity_search_with_relevance_scores(
        query,
        k=candidate_count,
        filter=build_chroma_filter(filters),
    )

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    ranked_chunks = []

    for document, score in results:
        chunk = chunks_by_id[document.metadata["chunk_id"]]

        if as_of is not None and chunk.metadata.expire_date is not None:
            if chunk.metadata.expire_date < as_of:
                continue

        ranked_chunks.append((chunk, float(score)))
        if len(ranked_chunks) == top_k:
            break

    return ranked_chunks