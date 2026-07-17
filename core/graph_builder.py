"""Build a compiled LangGraph from a vertical's components.

INDUSTRY-AGNOSTIC. Accepts agents + state class + config, returns a runnable graph.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from core.agents import human_escalation_node

if TYPE_CHECKING:
    from core.agents.resolver_base import ResolverAgent
    from core.agents.supervisor_base import SupervisorAgent
    from core.agents.triage_base import TriageAgent

logger = logging.getLogger(__name__)


def build_support_graph(
    *,
    state_class: type,
    triage: "TriageAgent",
    resolver: "ResolverAgent",
    supervisor: "SupervisorAgent",
    quality_threshold: float = 0.7,
    max_retries: int = 2,
    confidence_floor: float = 0.5,
    checkpointer: Any | None = None,
) -> Any:
    """Compose a Triage → Resolver → Supervisor → END graph with HITL.

    Args:
        state_class:        Vertical state TypedDict subclass.
        triage:             Configured TriageAgent instance.
        resolver:           Configured ResolverAgent instance.
        supervisor:         Configured SupervisorAgent instance.
        quality_threshold:  Score >= this passes (default 0.7).
        max_retries:        Resolver retry cap before forced human escalation.
        confidence_floor:   Triage confidence below this → human path.
        checkpointer:       Optional LangGraph checkpointer (defaults to MemorySaver).

    Returns:
        A compiled LangGraph application. Call ``.ainvoke(state)`` or
        ``.astream_events(state, version="v2")`` to run.
    """
    graph = StateGraph(state_class)

    # ── Nodes ───────────────────────────────────────────────────────
    graph.add_node("triage", triage)
    graph.add_node("resolver", resolver)
    graph.add_node("supervisor", supervisor)
    graph.add_node("human_escalation", human_escalation_node)

    # ── Entry ───────────────────────────────────────────────────────
    graph.set_entry_point("triage")

    # ── Conditional routing ─────────────────────────────────────────
    # Human-flagged and low-confidence requests still flow through
    # Resolver + Supervisor first, so the human reviewer receives a
    # quality-scored draft rather than a bare transcript. The escalation
    # decision is applied after scoring.
    def route_after_supervisor(state: dict) -> str:
        if (
            state.get("requires_human", False)
            or state.get("confidence", 1.0) < confidence_floor
        ):
            return "human_escalation"
        if state.get("quality_score", 0.0) >= quality_threshold:
            return "END"
        if state.get("retry_count", 0) >= max_retries:
            return "human_escalation"
        return "resolver"

    graph.add_edge("triage", "resolver")
    graph.add_edge("resolver", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"END": END, "resolver": "resolver", "human_escalation": "human_escalation"},
    )
    graph.add_edge("human_escalation", END)

    # ── Compile ─────────────────────────────────────────────────────
    compiled = graph.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["human_escalation"],   # pause for HITL
    )

    logger.info(
        "Compiled support graph: state=%s, quality_threshold=%.2f, max_retries=%d",
        state_class.__name__, quality_threshold, max_retries,
    )
    return compiled


__all__ = ["build_support_graph"]
