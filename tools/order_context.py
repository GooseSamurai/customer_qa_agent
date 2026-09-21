"""订单上下文查询工具的简单 Mock 实现。

这个文件只负责按订单编号返回测试数据。
它不决定是否应该查询订单，也不判断客服有没有违规。
"""


class OrderNotFoundError(ValueError):
    """订单不存在时使用的明确错误。"""


# 开发阶段使用的 Mock 数据，真实企业订单系统后续通过同样接口接入。
MOCK_ORDERS = {
    "order-001": {
        "order_id": "order-001",
        "product_name": "wireless earphones",
        "received_days": 12,
        "logistics_status": "delivered",
        "after_sale_status": "under_review",
    },
    "order-002": {
        "order_id": "order-002",
        "refund_status": "processing",
        "refund_expected_at": None,
    },
}


def get_order_context(
    order_id: str,
    fields: list[str] | None = None,
) -> dict[str, object]:
    """按订单编号返回订单上下文；fields 为空时返回全部字段。"""

    order = MOCK_ORDERS.get(order_id)

    # 查不到订单时不能伪造数据，调用方需要知道订单不存在。
    if order is None:
        raise OrderNotFoundError(f"order not found: {order_id}")

    # fields 未提供时返回完整订单上下文。
    if fields is None:
        return dict(order)

    # 只返回当前订单真实存在的字段，缺少的字段不凭空补值。
    return {field: order[field] for field in fields if field in order}