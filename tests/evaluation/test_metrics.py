"""基础评测指标测试。"""

from evaluation.metrics import binary_f1, micro_f1


def test_micro_f1_for_multilabel_sets() -> None:
    score = micro_f1([{"a", "b"}, {"c"}], [{"a"}, {"c", "d"}])

    assert round(score, 4) == 0.6667


def test_binary_f1() -> None:
    score = binary_f1([True, False, True], [True, True, True])

    assert round(score, 4) == 0.8