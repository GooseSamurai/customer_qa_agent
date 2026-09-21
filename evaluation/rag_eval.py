"""RAG 召回和重排评测。"""

import json
from datetime import date
from pathlib import Path

from rag.ingest import DocumentMetadata, KnowledgeChunk, ingest_manifest
from rag.rerank import rerank
from rag.retrieve import retrieve


def _source_ids(items) -> list[str]:
    return [item[0].source_id for item in items]


def evaluate_rag(
    chunks: list[KnowledgeChunk],
    cases: list[dict],
    as_of: date,
    recall_k: int = 3,
) -> dict:
    """计算 Recall@K 和 Rerank Top1/Top3。"""

    recall_hits = 0
    top1_hits = 0
    top3_hits = 0

    for case in cases:
        candidates = retrieve(
            case["query"],
            chunks,
            filters={"channel": "web"},
            top_k=recall_k,
            as_of=as_of,
        )
        if case["expected_source"] in _source_ids(candidates):
            recall_hits += 1

        ranked = rerank(case["query"], candidates)
        ranked_sources = _source_ids(ranked)
        if ranked_sources and ranked_sources[0] == case["expected_source"]:
            top1_hits += 1
        if case["expected_source"] in ranked_sources[:3]:
            top3_hits += 1

    total = len(cases)
    return {
        "recall_at_k": recall_hits / total if total else 0.0,
        "rerank_top1": top1_hits / total if total else 0.0,
        "rerank_top3": top3_hits / total if total else 0.0,
        "num_cases": total,
    }


def expired_policy_leak_rate(chunks: list[KnowledgeChunk], as_of: date) -> float:
    """检查已过期政策是否会在召回结果中出现。"""

    old_metadata = DocumentMetadata(
        source_id="old-refund-policy",
        title="旧退款政策",
        source_type="synthetic_sample",
        source_url="internal://old-refund-policy",
        channel="web",
        category="refund",
        policy_type="refund_policy",
        effective_date="2024-01-01",
        expire_date="2025-12-31",
    )
    old_chunk = KnowledgeChunk(
        source_id=old_metadata.source_id,
        chunk_id="old-refund-policy-chunk-1",
        text="旧版退款到账时间说明。",
        metadata=old_metadata,
    )

    results = retrieve(
        "退款到账时间",
        [old_chunk, *chunks],
        filters={"category": "refund"},
        top_k=10,
        as_of=as_of,
    )
    return 1.0 if old_metadata.source_id in _source_ids(results) else 0.0


def main() -> None:
    chunks = ingest_manifest(Path("data/knowledge/documents.json"))
    cases = [
        {"query": "客服承诺今晚退款到账", "expected_source": "refund_processing_rules"},
        {"query": "物流轨迹超过多久需要核查", "expected_source": "logistics_service_rules"},
        {"query": "七天无理由退货运费谁承担", "expected_source": "return_exchange_policy"},
        {"query": "优惠券能不能叠加使用", "expected_source": "promotion_price_rules"},
        {"query": "投诉什么情况下需要升级主管", "expected_source": "complaint_escalation_sop"},
    ]
    report = evaluate_rag(chunks, cases, as_of=date(2026, 9, 21))
    report["expired_policy_leak_rate"] = expired_policy_leak_rate(
        chunks,
        as_of=date(2026, 9, 21),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()