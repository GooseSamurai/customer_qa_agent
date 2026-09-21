"""SFT 数据构建测试。"""

import json

from schemas.finding import Finding
from tests.fixtures.cases import CASE_A, MOCK_RULES
from training.build_sft_data import build_sft_dataset


def sample_candidate(index: int) -> dict:
    finding = Finding.model_validate(
        {
            "rule_id": "rule-blame",
            "risk_type": "blame_shifting",
            "severity": "high",
            "reason": f"客服推诿客户 {index}。",
            "conversation_evidence": [
                {"message_id": "msg-a-002", "quote": "这个不归我们管"}
            ],
            "requires_external_verification": False,
            "claim": None,
            "required_evidence": [],
            "external_evidence": [],
        }
    )
    return {
        "review_id": f"review-{index}",
        "decision": "confirmed",
        "conversation": CASE_A["conversation"],
        "finding": finding.model_dump(mode="json"),
    }


def test_build_sft_dataset_writes_three_splits(tmp_path) -> None:
    """10 条候选应写成 train、valid、test，并产生统计文件。"""

    candidates_path = tmp_path / "candidates.jsonl"
    candidates_path.write_text(
        "\n".join(json.dumps(sample_candidate(i), ensure_ascii=False) for i in range(10)),
        encoding="utf-8",
    )
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(MOCK_RULES, ensure_ascii=False), encoding="utf-8")

    statistics = build_sft_dataset(candidates_path, rules_path, tmp_path / "sft")

    assert sum(statistics.values()) == 10
    assert statistics["train"] > 0
    assert statistics["valid"] == 1
    assert statistics["test"] == 1

    first = json.loads(
        (tmp_path / "sft" / "train.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert [message["role"] for message in first["messages"]] == ["user", "assistant"]
    assert "Conversation" in first["messages"][0]["content"]


def test_small_dataset_stays_in_train(tmp_path) -> None:
    """少于三条时不能伪造 valid/test。"""

    candidates_path = tmp_path / "candidates.jsonl"
    candidates_path.write_text(json.dumps(sample_candidate(1)), encoding="utf-8")
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(MOCK_RULES, ensure_ascii=False), encoding="utf-8")

    statistics = build_sft_dataset(candidates_path, rules_path, tmp_path / "sft")

    assert statistics == {"train": 1, "valid": 0, "test": 0}