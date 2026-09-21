"""单 Finding 的受控 Agent 工作流。"""

from datetime import date, datetime, timezone

from langgraph.graph import END, START, StateGraph

from agent.grounded_judge import GroundedJudge
from agent.router import Route, route_finding
from agent.state import AgentState
from evidence.verifier import verify_conversation_evidence
from model.qa_model import InvalidModelOutput
from rag.ingest import KnowledgeChunk
from schemas.evidence import KnowledgeEvidence, OrderEvidence
from schemas.finding import Finding
from tools.knowledge_tool import search_knowledge
from tools.order_context import OrderNotFoundError, get_order_context


def _verify_node(state: AgentState) -> dict:
    """先验证 Finding 的会话证据是否真实。"""

    finding = state["finding"]
    for evidence in finding.conversation_evidence:
        valid, error = verify_conversation_evidence(state["conversation"], evidence)
        if not valid:
            return {"status": "human_review", "error": error}

    return {"status": "running", "error": None}


def _route_node(state: AgentState) -> dict:
    """判断单个 Finding 的处理路径。"""

    return {"route": route_finding(state["finding"])}


def _direct_node(state: AgentState) -> dict:
    """纯语义问题不需要外部证据，直接确认结果。"""

    return {
        "final_finding": state["finding"],
        "status": "completed",
        "error": None,
    }


def _load_order_evidence(state: AgentState) -> list[OrderEvidence]:
    """读取当前会话关联订单的结构化事实。"""

    conversation = state["conversation"]
    if not conversation.order_ids:
        raise OrderNotFoundError("conversation has no order_id")

    evidence = []
    queried_at = datetime.now(timezone.utc)

    for order_id in conversation.order_ids:
        order = get_order_context(order_id)
        for field, value in order.items():
            if field == "order_id":
                continue
            evidence.append(
                OrderEvidence(
                    order_id=order_id,
                    field=field,
                    value=value,
                    queried_at=queried_at,
                )
            )

    return evidence


def _load_knowledge_evidence(
    state: AgentState,
    chunks: list[KnowledgeChunk],
    as_of: date | None,
) -> list[KnowledgeEvidence]:
    """按 Finding 的 Claim 检索业务知识。"""

    finding = state["finding"]
    query = finding.claim or finding.reason
    evidence = search_knowledge(
        query,
        chunks,
        filters={"channel": state["conversation"].channel},
        top_k=3,
        as_of=as_of,
    )

    if not evidence:
        raise ValueError("knowledge evidence not found")

    return evidence


def _order_node(state: AgentState, chunks: list[KnowledgeChunk], as_of: date | None) -> dict:
    """执行订单上下文路径。"""

    try:
        return {
            "order_evidence": _load_order_evidence(state),
            "status": "running",
            "error": None,
        }
    except OrderNotFoundError as exc:
        return {"status": "human_review", "error": str(exc)}


def _knowledge_node(state: AgentState, chunks: list[KnowledgeChunk], as_of: date | None) -> dict:
    """执行业务知识路径。"""

    try:
        return {
            "knowledge_evidence": _load_knowledge_evidence(state, chunks, as_of),
            "status": "running",
            "error": None,
        }
    except ValueError as exc:
        return {"status": "human_review", "error": str(exc)}


def _combined_node(state: AgentState, chunks: list[KnowledgeChunk], as_of: date | None) -> dict:
    """同时执行订单和知识两条取证路径。"""

    try:
        return {
            "order_evidence": _load_order_evidence(state),
            "knowledge_evidence": _load_knowledge_evidence(state, chunks, as_of),
            "status": "running",
            "error": None,
        }
    except (OrderNotFoundError, ValueError) as exc:
        return {"status": "human_review", "error": str(exc)}


def _judge_node(state: AgentState, judge: GroundedJudge) -> dict:
    """使用已有证据复判当前 Finding。"""

    external_evidence = [
        *state.get("order_evidence", []),
        *state.get("knowledge_evidence", []),
    ]

    try:
        final_finding = judge.judge(state["finding"], external_evidence)
        return {
            "final_finding": final_finding,
            "status": "completed",
            "error": None,
        }
    except InvalidModelOutput as exc:
        return {"status": "human_review", "error": str(exc)}


def _human_node(state: AgentState) -> dict:
    """统一人工复核出口。"""

    return {
        "final_finding": None,
        "status": "human_review",
        "error": state.get("error", "human review required"),
    }


def _after_verify(state: AgentState) -> str:
    return "human" if state.get("status") == "human_review" else "route"


def _route_target(state: AgentState) -> str:
    route = state["route"]
    if route is Route.DIRECT:
        return "direct"
    if route is Route.ORDER_CONTEXT:
        return "order"
    if route is Route.BUSINESS_KNOWLEDGE:
        return "knowledge"
    if route is Route.ORDER_AND_KNOWLEDGE:
        return "combined"
    return "human"


def _after_tool(state: AgentState) -> str:
    return "human" if state.get("status") == "human_review" else "judge"


def _after_judge(state: AgentState) -> str:
    return "human" if state.get("status") == "human_review" else "end"


def build_workflow(
    judge: GroundedJudge,
    chunks: list[KnowledgeChunk],
    as_of: date | None = None,
):
    """构建单 Finding 的 LangGraph 工作流。"""

    graph = StateGraph(AgentState)

    graph.add_node("verify", _verify_node)
    graph.add_node("route", _route_node)
    graph.add_node("direct", _direct_node)
    graph.add_node("order", lambda state: _order_node(state, chunks, as_of))
    graph.add_node("knowledge", lambda state: _knowledge_node(state, chunks, as_of))
    graph.add_node("combined", lambda state: _combined_node(state, chunks, as_of))
    graph.add_node("judge", lambda state: _judge_node(state, judge))
    graph.add_node("human", _human_node)

    graph.add_edge(START, "verify")
    graph.add_conditional_edges(
        "verify",
        _after_verify,
        {"route": "route", "human": "human"},
    )
    graph.add_conditional_edges(
        "route",
        _route_target,
        {
            "direct": "direct",
            "order": "order",
            "knowledge": "knowledge",
            "combined": "combined",
            "human": "human",
        },
    )
    graph.add_edge("direct", END)
    graph.add_conditional_edges(
        "order",
        _after_tool,
        {"judge": "judge", "human": "human"},
    )
    graph.add_conditional_edges(
        "knowledge",
        _after_tool,
        {"judge": "judge", "human": "human"},
    )
    graph.add_conditional_edges(
        "combined",
        _after_tool,
        {"judge": "judge", "human": "human"},
    )
    graph.add_conditional_edges(
        "judge",
        _after_judge,
        {"end": END, "human": "human"},
    )
    graph.add_edge("human", END)

    return graph.compile()


def run_workflow(
    conversation,
    findings: list[Finding],
    judge: GroundedJudge,
    chunks: list[KnowledgeChunk],
    as_of: date | None = None,
) -> list[AgentState]:
    """按单个 Finding 依次执行工作流。"""

    app = build_workflow(judge=judge, chunks=chunks, as_of=as_of)
    results = []

    for finding in findings:
        state = app.invoke(
            {
                "conversation": conversation,
                "finding": finding,
                "order_evidence": [],
                "knowledge_evidence": [],
                "final_finding": None,
                "status": "new",
                "error": None,
            }
        )
        results.append(state)

    return results