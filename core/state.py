"""Base state for the multi-agent support graph.

INDUSTRY-AGNOSTIC. No business keywords (no "education", "AMC", "parent", etc.).
Verticals extend ``BaseSupportState`` with industry-specific fields in their own ``state.py``.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


# ─────────────────────────────────────────────────────────────────────
# Type aliases
# ─────────────────────────────────────────────────────────────────────

Urgency = Literal["low", "medium", "high"]


# ─────────────────────────────────────────────────────────────────────
# BaseSupportState
# ─────────────────────────────────────────────────────────────────────

class BaseSupportState(TypedDict, total=False):
    """Universal state shared across all verticals.

    Field categories:
        Conversation:   messages, session_id, customer_id
        Triage outputs: intent, confidence, urgency, requires_human
        Resolver:       draft_response, tools_called, tool_results
        Supervisor:     quality_score, quality_feedback, final_response, citations
        Control flow:   retry_count, human_decision, resolved
        Meta:           vertical_name, mode

    Verticals MAY extend this TypedDict (subclassing) to add their own fields.
    Verticals MUST NOT redefine these existing fields.
    """

    # ── Conversation ────────────────────────────────────────────────
    messages: Annotated[list, add_messages]
    session_id: str
    customer_id: str

    # ── Triage outputs ──────────────────────────────────────────────
    intent: str               # vertical defines allowed values
    confidence: float         # 0.0..1.0
    urgency: Urgency
    requires_human: bool

    # ── Resolver outputs ────────────────────────────────────────────
    draft_response: str
    tools_called: list[str]
    tool_results: dict[str, Any]

    # ── Supervisor outputs ──────────────────────────────────────────
    quality_score: float      # 0.0..1.0
    quality_feedback: str
    final_response: str
    citations: list[dict]

    # ── Control flow ────────────────────────────────────────────────
    retry_count: int
    human_decision: str
    resolved: bool

    # ── Metadata ────────────────────────────────────────────────────
    vertical_name: str
    mode: Literal["mock", "real"]


# ─────────────────────────────────────────────────────────────────────
# Initial state helper
# ─────────────────────────────────────────────────────────────────────

def initial_state(
    *,
    session_id: str,
    customer_id: str,
    user_message: str,
    vertical_name: str,
    mode: Literal["mock", "real"] = "mock",
) -> dict:
    """Create a fresh state dict for a new request.

    The graph mutates this dict as it flows through Triage → Resolver → Supervisor.

    Args:
        session_id: Unique conversation identifier (used for thread persistence).
        customer_id: External user identifier from the calling application.
        user_message: The user's current message text.
        vertical_name: Industry vertical name (e.g. "education").
        mode: Either "mock" (no real LLM) or "real" (OpenAI API).

    Returns:
        State dict ready to pass to ``compiled_graph.invoke(state)``.
    """
    return {
        "messages": [{"role": "user", "content": user_message}],
        "session_id": session_id,
        "customer_id": customer_id,
        "intent": "",
        "confidence": 0.0,
        "urgency": "low",
        "requires_human": False,
        "draft_response": "",
        "tools_called": [],
        "tool_results": {},
        "quality_score": 0.0,
        "quality_feedback": "",
        "final_response": "",
        "citations": [],
        "retry_count": 0,
        "human_decision": "",
        "resolved": False,
        "vertical_name": vertical_name,
        "mode": mode,
    }


__all__ = ["BaseSupportState", "Urgency", "initial_state"]
