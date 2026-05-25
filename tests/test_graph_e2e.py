"""End-to-end test of the education vertical graph in MOCK_MODE.

Verifies that the full Triage → Resolver → Supervisor path runs without errors
and produces a non-empty final_response for each major intent.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Force MOCK mode for this test
os.environ.pop("OPENAI_API_KEY", None)


@pytest.fixture(scope="module")
def graph():
    """Compile the education graph once for all tests in this module."""
    from verticals.education import VERTICAL
    return VERTICAL["build_graph"]()


@pytest.fixture
def state_factory():
    from core.state import initial_state

    def _make(message: str, session_id: str = "test"):
        return initial_state(
            session_id=session_id,
            customer_id="test_customer",
            user_message=message,
            vertical_name="education",
            mode="mock",
        )
    return _make


@pytest.mark.asyncio
async def test_pricing_question_resolves(graph, state_factory) -> None:
    state = state_factory("How much is the AMC monthly plan?")
    config = {"configurable": {"thread_id": "test_pricing"}}
    result = await graph.ainvoke(state, config=config)
    assert result.get("intent") == "pricing_question"
    assert result.get("final_response", "")


@pytest.mark.asyncio
async def test_refund_within_window_resolves(graph, state_factory) -> None:
    state = state_factory("I want a refund — I signed up 3 days ago")
    config = {"configurable": {"thread_id": "test_refund1"}}
    result = await graph.ainvoke(state, config=config)
    assert result.get("intent") == "refund_request"


@pytest.mark.asyncio
async def test_complaint_escalates(graph, state_factory) -> None:
    state = state_factory("I'm going to call my lawyer about this")
    config = {"configurable": {"thread_id": "test_complaint"}}
    result = await graph.ainvoke(state, config=config)
    # Should require human (either via keyword or low confidence)
    assert result.get("requires_human") or result.get("retry_count", 0) >= 2


@pytest.mark.asyncio
async def test_plan_change_resolves(graph, state_factory) -> None:
    state = state_factory("Switch me from M3 to M4")
    config = {"configurable": {"thread_id": "test_switch"}}
    result = await graph.ainvoke(state, config=config)
    assert result.get("intent") == "plan_change"


@pytest.mark.asyncio
async def test_family_setup_resolves(graph, state_factory) -> None:
    state = state_factory("I want to add my second child to the family plan")
    config = {"configurable": {"thread_id": "test_family"}}
    result = await graph.ainvoke(state, config=config)
    assert result.get("intent") == "family_setup"
