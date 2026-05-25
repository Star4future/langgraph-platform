"""Tests for core/state.py — base state initialisation + invariants."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state import BaseSupportState, initial_state


def test_initial_state_required_fields() -> None:
    """initial_state must populate every field with a sensible default."""
    state = initial_state(
        session_id="s1",
        customer_id="cust_1",
        user_message="hello",
        vertical_name="education",
        mode="mock",
    )

    assert state["session_id"] == "s1"
    assert state["customer_id"] == "cust_1"
    assert state["vertical_name"] == "education"
    assert state["mode"] == "mock"
    assert state["retry_count"] == 0
    assert state["resolved"] is False
    assert state["requires_human"] is False
    assert isinstance(state["messages"], list)
    assert state["messages"][0]["content"] == "hello"


def test_initial_state_mode_default() -> None:
    """Mode defaults to 'mock' when not specified."""
    state = initial_state(
        session_id="s2",
        customer_id="x",
        user_message="hi",
        vertical_name="education",
    )
    assert state["mode"] == "mock"


def test_base_state_has_no_industry_fields() -> None:
    """BaseSupportState must remain industry-agnostic.

    This guards against accidentally adding education-specific fields
    (e.g. `student_id`, `plan_code`) into the base class.
    """
    industry_fields = {
        "student_id", "parent_id", "policy_id", "claim_id",
        "order_id", "appointment_id", "patient_id",
    }
    base_fields = set(BaseSupportState.__annotations__.keys())
    leaked = industry_fields & base_fields
    assert not leaked, f"Industry-specific fields leaked into BaseSupportState: {leaked}"
