"""QA Model 的结构化输出和分类评测。"""

import json
from pathlib import Path

from evaluation.metrics import binary_f1, micro_f1
from model.qa_model import InvalidModelOutput, QAModel
from schemas.conversation import Conversation
from schemas.finding import Finding
from schemas.qa_rule import QARule


def load_model_cases(path: str | Path) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _finding_labels(findings: list[Finding]) -> set[tuple[str, str]]:
    return {(finding.rule_id, finding.risk_type) for finding in findings}


def evaluate_model(qa_model: QAModel, cases: list[dict]) -> dict:
    """在同一测试集上计算 QA Model 指标。"""

    expected_labels = []
    predicted_labels = []
    expected_triggers = []
    predicted_triggers = []
    schema_success = 0
    evidence_hits = 0

    for case in cases:
        conversation = Conversation.model_validate(case["conversation"])
        rules = [QARule.model_validate(item) for item in case["rules"]]

        try:
            findings = qa_model.analyze(conversation, rules)
            schema_success += 1
        except InvalidModelOutput:
            findings = []

        expected_label = {tuple(item.split("|", 1)) for item in case["expected_labels"]}
        predicted_label = _finding_labels(findings)
        expected_labels.append(expected_label)
        predicted_labels.append(predicted_label)

        expected_trigger = bool(case["expected_external_verification"])
        expected_triggers.append(expected_trigger)
        predicted_triggers.append(any(f.requires_external_verification for f in findings))

        matched = False
        for finding in findings:
            if (finding.rule_id, finding.risk_type) not in expected_label:
                continue
            for evidence in finding.conversation_evidence:
                if (
                    evidence.message_id == case["expected_message_id"]
                    and case["expected_quote"] in evidence.quote
                ):
                    matched = True
                    break
        if matched:
            evidence_hits += 1

    total = len(cases)
    return {
        "finding_classification_f1": micro_f1(expected_labels, predicted_labels),
        "external_verification_trigger_f1": binary_f1(expected_triggers, predicted_triggers),
        "evidence_localization_accuracy": evidence_hits / total if total else 0.0,
        "schema_success_rate": schema_success / total if total else 0.0,
        "num_cases": total,
    }