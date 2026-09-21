"""业务知识工具测试。"""

from rag.ingest import DocumentMetadata, ingest_document
from schemas.evidence import KnowledgeEvidence
from tools.knowledge_tool import search_knowledge


def test_search_knowledge_returns_evidence() -> None:
    """知识工具应把召回片段转换为 KnowledgeEvidence。"""

    metadata = DocumentMetadata(
        source_id="after-sale-policy",
        title="售后规则",
        source_url="https://example.com/after-sale",
        channel="web",
        category="after_sale",
        policy_type="return_policy",
    )
    chunks = ingest_document("符合条件的商品支持七天无理由退货。", metadata)

    evidence = search_knowledge("七天无理由退货", chunks, top_k=1)

    assert len(evidence) == 1
    assert isinstance(evidence[0], KnowledgeEvidence)
    assert evidence[0].source_id == "after-sale-policy"
    assert evidence[0].chunk_id == "after-sale-policy-chunk-1"