"""T005 代表性客服案例和 Mock 企业数据。

这里只放测试数据，不写判断逻辑。
"""

CASE_A = {
    "conversation": {
        "conversation_id": "conv-case-a",
        "channel": "web",
        "customer_id": "customer-a",
        "agent_id": "agent-a",
        "order_ids": [],
        "start_time": "2026-09-21T10:00:00+08:00",
        "messages": [
            {
                "message_id": "msg-a-001",
                "role": "customer",
                "timestamp": "2026-09-21T10:00:00+08:00",
                "text": "我已经问三次了，你们到底怎么处理？",
            },
            {
                "message_id": "msg-a-002",
                "role": "agent",
                "timestamp": "2026-09-21T10:00:10+08:00",
                "text": "这个不归我们管，你自己联系物流。",
            },
        ],
    }
}

CASE_B = {
    "conversation": {
        "conversation_id": "conv-case-b",
        "channel": "web",
        "customer_id": "customer-b",
        "agent_id": "agent-b",
        "order_ids": ["order-001"],
        "start_time": "2026-09-21T11:00:00+08:00",
        "messages": [
            {
                "message_id": "msg-b-001",
                "role": "customer",
                "timestamp": "2026-09-21T11:00:00+08:00",
                "text": "耳机坏了，买了十几天，可以退吗？",
            },
            {
                "message_id": "msg-b-002",
                "role": "agent",
                "timestamp": "2026-09-21T11:00:10+08:00",
                "text": "超过 7 天都不能退。",
            },
        ],
    }
}

CASE_C = {
    "conversation": {
        "conversation_id": "conv-case-c",
        "channel": "web",
        "customer_id": "customer-c",
        "agent_id": "agent-c",
        "order_ids": ["order-002"],
        "start_time": "2026-09-21T12:00:00+08:00",
        "messages": [
            {
                "message_id": "msg-c-001",
                "role": "customer",
                "timestamp": "2026-09-21T12:00:00+08:00",
                "text": "这笔退款什么时候到账？",
            },
            {
                "message_id": "msg-c-002",
                "role": "agent",
                "timestamp": "2026-09-21T12:00:10+08:00",
                "text": "今晚肯定到账。",
            },
        ],
    }
}

MOCK_RULES = [
    {
        "rule_id": "rule-blame",
        "name": "禁止推诿客户",
        "dimension": "服务态度",
        "description": "客服不得将客户问题直接推给其他方。",
        "positive_condition": "客服直接将问题推给客户自行处理",
        "exclude_condition": None,
        "severity": "high",
        "need_external_fact": False,
        "enabled": True,
        "version": "v1",
    },
    {
        "rule_id": "rule-after-sale",
        "name": "售后资格解释准确",
        "dimension": "业务准确性",
        "description": "客服说明售后资格时必须符合有效业务规则。",
        "positive_condition": "客服说明退货或售后资格",
        "exclude_condition": None,
        "severity": "high",
        "need_external_fact": True,
        "enabled": True,
        "version": "v1",
    },
    {
        "rule_id": "rule-refund-promise",
        "name": "不得承诺无依据到账时间",
        "dimension": "无依据承诺",
        "description": "客服不得承诺没有业务依据的具体到账时间。",
        "positive_condition": "客服承诺具体到账时间",
        "exclude_condition": None,
        "severity": "high",
        "need_external_fact": True,
        "enabled": True,
        "version": "v1",
    },
]

MOCK_ORDER_CONTEXTS = {
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

MOCK_KNOWLEDGE_DOCUMENTS = [
    {
        "source_id": "after-sale-policy",
        "chunk_id": "chunk-001",
        "text": "符合条件的商品支持七天无理由退货。",
        "metadata": {"version": "v1", "effective_date": "2026-01-01"},
    }
]