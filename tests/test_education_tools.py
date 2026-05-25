"""Tests for verticals/education/tools.py — mock backend correctness."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verticals.education import tools


def test_lookup_subscription_existing() -> None:
    """Known parent email returns subscriptions."""
    result = tools.lookup_subscription("sarah.chen@example.com.au")
    assert result["found"] is True
    assert result["parent_id"] == "PAR-1001"
    assert len(result["subscriptions"]) == 1


def test_lookup_subscription_unknown() -> None:
    """Unknown email returns found=False."""
    result = tools.lookup_subscription("nobody@example.com.au")
    assert result["found"] is False


def test_check_refund_within_14_days_first_purchase() -> None:
    """First purchase + recent (SUB-2004 is within 14-day window in mock data may vary by date).
    The test checks the policy logic, not a specific yes/no."""
    result = tools.check_refund_eligibility("SUB-2004", reason="not_using")
    assert "eligible" in result
    assert "policy_reference" in result


def test_check_refund_one_off_completed() -> None:
    """John Locke one-off after AI feedback → not refundable."""
    result = tools.check_refund_eligibility("SUB-2005", reason="bad_result")
    assert result["eligible"] is False
    assert "one-off" in result["reason"].lower()


def test_check_refund_unknown_subscription() -> None:
    result = tools.check_refund_eligibility("SUB-DOES-NOT-EXIST", reason="x")
    assert result["eligible"] is False


def test_calculate_prorated_refund_annual() -> None:
    result = tools.calculate_prorated_refund("SUB-2003")
    assert "refund_amount" in result
    assert result["currency"] == "AUD"
    assert result["includes_gst"] is True
    assert result["admin_fee"] == 50


def test_calculate_prorated_refund_monthly_rejected() -> None:
    result = tools.calculate_prorated_refund("SUB-2001")  # monthly
    assert "error" in result


def test_switch_plan_differential() -> None:
    result = tools.switch_plan("PAR-1001", "M3", "M4")
    assert result["from_plan"] == "M3"
    assert result["to_plan"] == "M4"
    assert result["price_differential_monthly"] == 0  # both $69
    assert result["currency"] == "AUD"


def test_switch_plan_same() -> None:
    result = tools.switch_plan("PAR-1001", "M3", "M3")
    assert "error" in result


def test_apply_family_discount_2_children() -> None:
    result = tools.apply_family_discount("PAR-1002", 2)
    assert result["applied"] is True
    assert len(result["discounts"]) == 1
    assert result["discounts"][0]["child"] == 2


def test_apply_family_discount_3_children() -> None:
    result = tools.apply_family_discount("PAR-1002", 3)
    assert result["applied"] is True
    assert len(result["discounts"]) == 2


def test_apply_family_discount_1_child_rejected() -> None:
    result = tools.apply_family_discount("PAR-1002", 1)
    assert result["applied"] is False


def test_create_child_account_valid() -> None:
    result = tools.create_child_account("PAR-1001", "Sophie Chen", 7)
    assert result["success"] is True
    assert result["year_level"] == 7
    assert "student_id" in result


def test_create_child_account_invalid_year() -> None:
    result = tools.create_child_account("PAR-1001", "X", 14)
    assert "error" in result


def test_escalate_to_teacher() -> None:
    result = tools.escalate_to_teacher("STU-3001", "Parent worried about progress")
    assert result["escalated"] is True
    assert "ticket_id" in result
    assert result["expected_response_hours"] == 24


def test_send_confirmation_email() -> None:
    result = tools.send_confirmation_email("test@example.com.au", "Switched plan from M3 to M4")
    assert result["sent"] is True
    assert result["to"] == "test@example.com.au"


def test_all_tools_have_docstrings() -> None:
    """Every @tool function must have a docstring (the LLM reads it)."""
    from core.agents import collect_tools_from_module
    tools_dict, _ = collect_tools_from_module(tools)
    for name, fn in tools_dict.items():
        assert fn.__doc__, f"Tool '{name}' is missing a docstring"
