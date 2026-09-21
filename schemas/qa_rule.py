"""企业质检规则的数据契约。

这个文件只描述“一条质检规则包含哪些字段、字段是什么类型、哪些值合法”。
它不负责数据库保存，也不负责把规则拼进 Prompt。
"""

from typing import Literal

from pydantic import BaseModel

# 当前只定义三个严重程度。
# 使用 Literal 后，severity 只能取这三个值，写错会在入口直接失败。
RuleSeverity = Literal["low", "medium", "high"]


class QARule(BaseModel):
    """企业侧提供的一条质检规则。"""

    # 规则编号。用于把质检结果关联回具体规则。
    rule_id: str

    # 规则名称。例如“禁止推诿客户”。
    name: str

    # 质检维度。例如“服务态度”“问题解决”“业务准确性”。
    dimension: str

    # 规则说明。给运营和开发人员阅读，不直接作为模型 Prompt。
    description: str

    # 正面触发条件。满足这个条件时，规则可能被触发。
    positive_condition: str

    # 排除条件。满足这个条件时，即使命中正面条件，也可能不判违规。
    # 不是所有规则都有排除条件，因此允许为空。
    exclude_condition: str | None = None

    # 风险严重程度，只能是 low、medium 或 high。
    severity: RuleSeverity

    # 这条规则是否可能需要查询订单或业务知识等外部事实。
    # 它只表达“可能需要”，不表示本任务会真的调用外部能力。
    need_external_fact: bool

    # 规则当前是否启用。停用规则仍然可以被保存和查询。
    enabled: bool

    # 企业规则版本，例如 "v1"、"2026-09"。
    # 保留版本信息是为了后续审计时知道当时使用了哪一版规则。
    version: str