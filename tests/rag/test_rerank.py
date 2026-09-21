"""重排测试。"""

from rag.ingest import DocumentMetadata, KnowledgeChunk
from rag.rerank import rerank


def metadata(source_id: str) -> DocumentMetadata:
    """返回测试用文档元数据。"""

    return DocumentMetadata(
        source_id=source_id,
        title=source_id,
        source_url=f"https://example.com/{source_id}",
        channel="web",
        category="after_sale",
        policy_type="return_policy",
    )


def test_rerank_puts_exact_query_match_first() -> None:
    """完整包含 query 的片段应排在前面，同时保留原片段对象。"""

    first = KnowledgeChunk(
        source_id="source-a",
        chunk_id="chunk-a",
        text="先看这条",
        metadata=metadata("source-a"),
    )
    second = KnowledgeChunk(
        source_id="source-b",
        chunk_id="chunk-b",
        text="退款到账说明",
        metadata=metadata("source-b"),
    )

    ranked = rerank("退款到账", [(first, 0.9), (second, 0.1)])

    assert ranked[0][0] is second
    assert ranked[0][0].chunk_id == "chunk-b"