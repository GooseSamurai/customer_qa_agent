"""把人工复核结果导出为 SFT 候选数据。"""

import json
from pathlib import Path

from db.models import ReviewDecision
from db.repository import SQLiteRepository


def export_sft_candidates(
    repository: SQLiteRepository,
    output_path: str | Path,
) -> int:
    """导出 confirmed 和 correction 复核样本。"""

    candidates = []

    for review in repository.list_reviews():
        if review.decision is ReviewDecision.FALSE_POSITIVE:
            continue

        record = repository.get_finding_record(review.finding_id)
        if record is None:
            continue

        finding = review.corrected_finding or record["finding"]
        conversation = repository.get_case(record["case_id"])
        if conversation is None:
            continue

        candidates.append(
            {
                "review_id": review.review_id,
                "decision": review.decision.value,
                "conversation": conversation.model_dump(mode="json"),
                "finding": finding.model_dump(mode="json"),
            }
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        for candidate in candidates:
            file.write(json.dumps(candidate, ensure_ascii=False) + "\n")

    return len(candidates)