"""知识文档入库测试。"""

import pytest

from rag.ingest import DocumentMetadata, ingest_document


def sample_metadata() -> DocumentMetadata:
    """返回一份最小文档元数据。"""

    return DocumentMetadata(
        source_id="after-sale-policy",
        title="售后规则",
        source_url="https://example.com/after-sale",
        channel="web",
        category="after_sale",
        policy_type="return_policy",
        effective_date="2026-01-01",
        expire_date="2026-12-31",
    )


def test_markdown_document_is_split_by_headings() -> None:
    """Markdown 标题应生成独立 chunk，并保留来源和 section。"""

    text = "# 售后规则\n\n## 退货条件\n\n符合条件可以退货。\n\n## 运费承担\n\n无理由退货运费由消费者承担。"

    chunks = ingest_document(text, sample_metadata())

    assert len(chunks) >= 2
    assert chunks[0].source_id == "after-sale-policy"
    assert any(chunk.section == "退货条件" for chunk in chunks)
    assert chunks[-1].metadata.channel == "web"


def test_empty_document_is_rejected() -> None:
    """没有正文的文档不能生成知识片段。"""

    with pytest.raises(ValueError):
        ingest_document("  \n\n  ", sample_metadata())