"""Human-in-the-loop node.

When this node is reached, the graph is paused (via LangGraph's
``interrupt_before=["human_escalation"]``) and waits for a human to
provide a decision via the ``/api/resume`` endpoint.

INDUSTRY-AGNOSTIC.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def human_escalation_node(state: dict) -> dict:
    """Render the message presented to the human reviewer + carry over decision.

    When LangGraph resumes (after operator calls /api/resume with human_decision),
    this node runs and writes the human input into the final response.

    Args:
        state: BaseSupportState dict.

    Returns:
        Partial update: final_response (composed from human_decision)
                        + resolved=True
                        + appended audit metadata.
    """
    human_decision = state.get("human_decision", "")

    if not human_decision:
        # Graph paused, waiting for input — emit placeholder so frontend sees status
        logger.info(
            "Human escalation: session=%s customer=%s intent=%s — awaiting human input",
            state.get("session_id"),
            state.get("customer_id"),
            state.get("intent"),
        )
        return {
            "final_response": _waiting_message(state),
            "resolved": False,
        }

    # Human has provided a decision → finalise the response
    audit_log = {
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "reason": _escalation_reason(state),
        "human_decision": human_decision,
    }
    logger.info("Human resolution: %s", audit_log)

    return {
        "final_response": human_decision,
        "resolved": True,
        "tool_results": {
            **state.get("tool_results", {}),
            "_escalation_audit": audit_log,
        },
    }


# ─────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────

def _escalation_reason(state: dict) -> str:
    """Compose a short reason string for the audit log."""
    if state.get("requires_human"):
        return "triage_flagged_high_risk"
    if state.get("confidence", 1.0) < 0.5:
        return f"low_triage_confidence ({state['confidence']:.2f})"
    if state.get("retry_count", 0) >= 2:
        return "supervisor_retry_exhausted"
    return "unspecified"


def _waiting_message(state: dict) -> str:
    """User-facing message shown while the graph is paused.

    Verticals can override this via config if they want bespoke wording.
    """
    return (
        "I've escalated this to a member of our team. "
        "They'll review your request and follow up — typically within "
        "1 business day. "
        f"Reference: {state.get('session_id', 'unknown')[:8]}"
    )
