"""RAG 评测逻辑测试。"""

from datetime import date

from evaluation.rag_eval import evaluate_rag
from rag.ingest import DocumentMetadata, KnowledgeChunk


def test_rag_eval_counts_recall_and_rerank(monkeypatch) -> None:
    chunk = KnowledgeChunk(
        source_id="expected-source",
        chunk_id="chunk-1",
        text="退款规则",
        metadata=DocumentMetadata(
            source_id="expected-source",
            title="退款规则",
            source_url="internal://refund",
            channel="web",
            category="refund",
            policy_type="refund_policy",
        ),
    )
    monkeypatch.setattr(
        "evaluation.rag_eval.retrieve",
        lambda *args, **kwargs: [(chunk, 0.9)],
    )
    monkeypatch.setattr(
        "evaluation.rag_eval.rerank",
        lambda *args, **kwargs: [(chunk, 1.0)],
    )

    report = evaluate_rag(
        [chunk],
        [{"query": "退款", "expected_source": "expected-source"}],
        as_of=date(2026, 9, 21),
    )

    assert report["recall_at_k"] == 1.0
    assert report["rerank_top1"] == 1.0
    assert report["rerank_top3"] == 1.0