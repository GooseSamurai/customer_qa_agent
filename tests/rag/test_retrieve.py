"""基础知识召回测试。"""

from datetime import date

from rag.ingest import DocumentMetadata, ingest_document
from rag.retrieve import retrieve


def metadata(source_id: str, expire_date: str | None) -> DocumentMetadata:
    """返回测试用文档元数据。"""

    return DocumentMetadata(
        source_id=source_id,
        title=source_id,
        source_url=f"https://example.com/{source_id}",
        channel="web",
        category="refund",
        policy_type="refund_policy",
        effective_date="2026-01-01",
        expire_date=expire_date,
    )


def test_retrieve_filters_and_excludes_expired_chunks() -> None:
    """召回应支持元数据过滤，并排除已经过期的片段。"""

    new_chunks = ingest_document("退款到账时间说明", metadata("new-policy", "2026-12-31"))
    old_chunks = ingest_document("退款到账时间说明", metadata("old-policy", "2025-12-31"))

    results = retrieve(
        "退款到账",
        new_chunks + old_chunks,
        filters={"channel": "web", "category": "refund"},
        as_of=date(2026, 9, 21),
    )

    assert len(results) == 1
    assert results[0][0].source_id == "new-policy"


def test_retrieve_keeps_source_and_chunk_ids() -> None:
    """召回结果必须保留可追溯的 source_id 和 chunk_id。"""

    chunks = ingest_document("符合条件可以退货", metadata("after-sale-policy", None))

    results = retrieve("退货", chunks, top_k=1)

    chunk, score = results[0]
    assert chunk.source_id == "after-sale-policy"
    assert chunk.chunk_id == "after-sale-policy-chunk-1"
    assert score > 0