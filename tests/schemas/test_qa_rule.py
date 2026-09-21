"""QARule 数据结构的正常与异常测试。"""

import pytest
from pydantic import ValidationError

from schemas.qa_rule import QARule


def valid_rule_payload() -> dict:
    """返回一条通过校验的最小质检规则。"""

    return {
        "rule_id": "rule-001",
        "name": "禁止推诿客户",
        "dimension": "服务态度",
        "description": "客服不得将客户问题简单推给其他方。",
        "positive_condition": "客服直接将问题推给客户自行处理",
        "exclude_condition": None,
        "severity": "high",
        "need_external_fact": False,
        "enabled": True,
        "version": "v1",
    }


def test_valid_rule_is_parsed() -> None:
    """正常规则应被解析成 QARule 对象。"""

    rule = QARule.model_validate(valid_rule_payload())

    assert rule.rule_id == "rule-001"
    assert rule.severity == "high"
    assert rule.enabled is True


def test_exclude_condition_is_optional() -> None:
    """没有排除条件时，应使用默认值 None。"""

    payload = valid_rule_payload()
    del payload["exclude_condition"]

    rule = QARule.model_validate(payload)

    assert rule.exclude_condition is None


def test_disabled_rule_is_valid() -> None:
    """停用规则仍然是合法数据，是否启用由 enabled 字段表达。"""

    payload = valid_rule_payload()
    payload["enabled"] = False

    rule = QARule.model_validate(payload)

    assert rule.enabled is False


def test_invalid_severity_is_rejected() -> None:
    """severity 只能使用 low、medium 或 high。"""

    payload = valid_rule_payload()
    payload["severity"] = "critical"

    with pytest.raises(ValidationError):
        QARule.model_validate(payload)