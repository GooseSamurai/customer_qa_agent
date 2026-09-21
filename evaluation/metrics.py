"""评测脚本共用的基础指标。"""


def micro_f1(expected: list[set], predicted: list[set]) -> float:
    """计算多标签集合的 micro F1。"""

    true_positive = 0
    false_positive = 0
    false_negative = 0

    for expected_set, predicted_set in zip(expected, predicted):
        true_positive += len(expected_set & predicted_set)
        false_positive += len(predicted_set - expected_set)
        false_negative += len(expected_set - predicted_set)

    if true_positive + false_positive + false_negative == 0:
        return 1.0

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def binary_f1(expected: list[bool], predicted: list[bool]) -> float:
    """计算布尔分类的 F1。"""

    true_positive = sum(e and p for e, p in zip(expected, predicted))
    false_positive = sum((not e) and p for e, p in zip(expected, predicted))
    false_negative = sum(e and (not p) for e, p in zip(expected, predicted))

    if true_positive + false_positive + false_negative == 0:
        return 1.0

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0