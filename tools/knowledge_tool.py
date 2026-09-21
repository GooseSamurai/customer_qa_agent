"""业务知识检索工具的最简单封装。

它只负责检索和转换成 KnowledgeEvidence。
是否调用这个工具，由后续 Agent 或流程决定。
"""

from datetime import date

from rag.ingest import KnowledgeChunk
from rag.rerank import rerank
from rag.retrieve import retrieve
from schemas.evidence import KnowledgeEvidence


def search_knowledge(
    query: str,
    chunks: list[KnowledgeChunk],
    filters: dict[str, object] | None = None,
    top_k: int = 3,
    as_of: date | None = None,
) -> list[KnowledgeEvidence]:
    """召回知识片段并转换成可追溯的证据对象。"""

    candidates = retrieve(query, chunks, filters=filters, top_k=top_k, as_of=as_of)
    ranked = rerank(query, candidates)

    evidence = []
    for chunk, _score in ranked:
        evidence.append(
            KnowledgeEvidence(
                source_id=chunk.source_id,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                metadata=chunk.metadata.model_dump(mode="json"),
            )
        )

    return evidence