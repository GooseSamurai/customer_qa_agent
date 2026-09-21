"""Agent 确定性评测测试。"""

from evaluation.agent_eval import evaluate_agent


def test_agent_metrics_are_complete() -> None:
    report = evaluate_agent()

    assert report["routing_accuracy"] == 1.0
    assert report["evidence_validation_accuracy"] == 1.0
    assert report["tool_argument_accuracy"] == 1.0