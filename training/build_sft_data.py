"""把人工复核候选数据转换成 SFT 训练格式。"""

import json
import random
from pathlib import Path

from model.prompt import build_qa_prompt
from schemas.conversation import Conversation
from schemas.finding import Finding
from schemas.qa_rule import QARule


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _split_rows(rows: list[dict], seed: int) -> dict[str, list[dict]]:
    """按固定随机种子切分 train / valid / test。"""

    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)

    if len(shuffled) < 3:
        return {"train": shuffled, "valid": [], "test": []}

    test_count = max(1, len(shuffled) // 10)
    valid_count = max(1, len(shuffled) // 10)
    test_rows = shuffled[:test_count]
    valid_rows = shuffled[test_count:test_count + valid_count]
    train_rows = shuffled[test_count + valid_count:]
    return {"train": train_rows, "valid": valid_rows, "test": test_rows}


def build_sft_dataset(
    candidates_path: str | Path,
    rules_path: str | Path,
    output_dir: str | Path,
    seed: int = 42,
) -> dict[str, int]:
    """生成 train.jsonl、valid.jsonl、test.jsonl 和统计文件。"""

    candidates = _load_jsonl(Path(candidates_path))
    rules = [
        QARule.model_validate(item)
        for item in json.loads(Path(rules_path).read_text(encoding="utf-8"))
    ]

    examples = []
    for candidate in candidates:
        conversation = Conversation.model_validate(candidate["conversation"])
        finding = Finding.model_validate(candidate["finding"])
        assistant_output = {"findings": [finding.model_dump(mode="json")]}
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": build_qa_prompt(conversation, rules)},
                    {
                        "role": "assistant",
                        "content": json.dumps(assistant_output, ensure_ascii=False),
                    },
                ],
                "metadata": {
                    "review_id": candidate["review_id"],
                    "decision": candidate["decision"],
                },
            }
        )

    splits = _split_rows(examples, seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    statistics = {}
    for split_name, rows in splits.items():
        _write_jsonl(output / f"{split_name}.jsonl", rows)
        statistics[split_name] = len(rows)

    (output / "statistics.json").write_text(
        json.dumps(statistics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return statistics