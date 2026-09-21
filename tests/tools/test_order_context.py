"""订单上下文 Mock 工具测试。"""

import pytest

from tools.order_context import OrderNotFoundError, get_order_context


def test_known_order_returns_full_context() -> None:
    """查询已知订单时，应返回 Mock 中的完整字段。"""

    context = get_order_context("order-001")

    assert context["order_id"] == "order-001"
    assert context["received_days"] == 12
    assert context["logistics_status"] == "delivered"


def test_selected_fields_are_returned() -> None:
    """指定 fields 时，只返回当前订单真实存在的字段。"""

    context = get_order_context("order-001", ["order_id", "received_days", "missing"])

    assert context == {"order_id": "order-001", "received_days": 12}


def test_missing_order_returns_explicit_error() -> None:
    """订单不存在时，应抛出明确错误，而不是伪造订单上下文。"""

    with pytest.raises(OrderNotFoundError):
        get_order_context("missing-order")