"""Education vertical tools — AcmeAcademy parent service mock functions.

ALL FUNCTIONS ARE MOCK. They simulate a real backend (Stripe + DB) for
demo and eval purposes. Replace with real API calls in production deploy.

Each tool decorated with ``@tool`` is auto-collected into the vertical's
tool registry by ``core.agents.collect_tools_from_module``.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from core.agents import tool

# ─────────────────────────────────────────────────────────────────────
# Mock DB loader
# ─────────────────────────────────────────────────────────────────────

_DB_PATH = Path(__file__).parent / "data" / "mock_db.json"


def _load_db() -> dict:
    if not _DB_PATH.exists():
        return {"subscriptions": {}, "parents": {}, "students": {}, "plans": {}}
    with open(_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────────────

@tool
def lookup_subscription(user_email: str) -> dict:
    """Look up a parent's active subscription(s) by email address.

    Returns parent_id, list of subscriptions (each with plan_code, status, start_date,
    next_renewal, amount), and any active discounts.
    """
    db = _load_db()
    for parent_id, parent in db.get("parents", {}).items():
        if parent.get("email", "").lower() == user_email.lower():
            subs = [
                db["subscriptions"].get(sid, {})
                for sid in parent.get("subscription_ids", [])
            ]
            return {
                "parent_id": parent_id,
                "name": parent.get("name"),
                "subscriptions": subs,
                "active_discounts": parent.get("active_discounts", []),
                "found": True,
            }
    return {"found": False, "message": f"No account found for {user_email}"}


@tool
def check_refund_eligibility(subscription_id: str, reason: str) -> dict:
    """Check whether a subscription is eligible for a refund under AcmeAcademy policy.

    Policy:
    - 14-day money-back guarantee on first purchase (full refund, no questions)
    - Beyond 14 days: prorated refund eligible for unused months on annual plans
    - One-off products (Starter pack, John Locke submissions) non-refundable after AI feedback delivered
    - Refunds > AU$200 require human approval
    """
    db = _load_db()
    sub = db.get("subscriptions", {}).get(subscription_id)
    if not sub:
        return {"eligible": False, "reason": "Subscription not found"}

    start = datetime.strptime(sub["start_date"], "%Y-%m-%d").date()
    days_since_start = (date.today() - start).days

    if sub.get("is_one_off") and sub.get("ai_feedback_delivered"):
        return {
            "eligible": False,
            "reason": "One-off product with AI feedback already delivered",
            "policy_reference": "Refunds & Cancellation §3",
        }

    if days_since_start <= 14 and sub.get("is_first_purchase", False):
        return {
            "eligible": True,
            "refund_type": "full",
            "amount": sub.get("amount_paid", 0),
            "policy_reference": "14-day money-back guarantee",
            "requires_human_approval": False,
        }

    if sub.get("plan_type") == "annual" and sub.get("status") == "active":
        return {
            "eligible": True,
            "refund_type": "prorated",
            "policy_reference": "Annual plan prorated refund",
            "requires_human_approval": True,
            "next_step": "Call calculate_prorated_refund for exact amount",
        }

    return {
        "eligible": False,
        "reason": "Monthly plan past 14-day window; cancel anytime instead",
        "policy_reference": "Cancellation policy",
    }


@tool
def calculate_prorated_refund(subscription_id: str) -> dict:
    """Calculate the prorated refund amount for an annual subscription.

    Formula: (months_remaining / 12) * annual_amount, minus AU$50 admin fee.
    Refunds over AU$200 require human approval (flag in response).
    """
    db = _load_db()
    sub = db.get("subscriptions", {}).get(subscription_id)
    if not sub or sub.get("plan_type") != "annual":
        return {"error": "Subscription not annual or not found"}

    start = datetime.strptime(sub["start_date"], "%Y-%m-%d").date()
    end_of_term = start + timedelta(days=365)
    months_remaining = max(0, (end_of_term - date.today()).days / 30)

    annual_amount = sub.get("amount_paid", 0)
    refund = max(0, round((months_remaining / 12) * annual_amount - 50, 2))

    return {
        "subscription_id": subscription_id,
        "annual_amount": annual_amount,
        "months_remaining": round(months_remaining, 1),
        "admin_fee": 50,
        "refund_amount": refund,
        "currency": "AUD",
        "includes_gst": True,
        "requires_human_approval": refund > 200,
    }


@tool
def switch_plan(parent_id: str, from_plan: str, to_plan: str) -> dict:
    """Switch a parent's subscription from one module to another.

    Valid plans: M1 (Writing), M3 (AMC), M4 (AIMO), M5 (Science), bundle.
    Calculates upgrade/downgrade differential; returns confirmation summary.
    """
    db = _load_db()
    plans = db.get("plans", {})

    if from_plan not in plans or to_plan not in plans:
        return {"error": f"Unknown plan. Valid: {list(plans.keys())}"}

    if from_plan == to_plan:
        return {"error": "Source and target plans are identical"}

    from_price = plans[from_plan]["monthly_price"]
    to_price = plans[to_plan]["monthly_price"]
    differential = to_price - from_price

    return {
        "parent_id": parent_id,
        "from_plan": from_plan,
        "from_plan_name": plans[from_plan]["name"],
        "to_plan": to_plan,
        "to_plan_name": plans[to_plan]["name"],
        "price_differential_monthly": differential,
        "currency": "AUD",
        "includes_gst": True,
        "switch_effective": "next billing cycle",
        "progress_carried_over": from_plan in ("M3", "M4") and to_plan in ("M3", "M4"),
        "confirmation_id": f"SWITCH-{parent_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }


@tool
def apply_family_discount(parent_id: str, child_count: int) -> dict:
    """Apply AcmeAcademy Family Plan discount.

    Policy:
    - 2nd child: 50% off any monthly or annual plan
    - 3rd child: free on annual tiers only
    - Discount applied automatically to youngest active subscription
    """
    if child_count < 2:
        return {
            "applied": False,
            "reason": "Family discount requires 2+ children enrolled",
        }

    discounts = []
    if child_count >= 2:
        discounts.append({"child": 2, "discount": "50% off", "applies_to": "any plan"})
    if child_count >= 3:
        discounts.append({"child": 3, "discount": "100% off", "applies_to": "annual plans only"})

    return {
        "applied": True,
        "parent_id": parent_id,
        "child_count": child_count,
        "discounts": discounts,
        "currency": "AUD",
        "policy_reference": "Family Plans & Bundles",
        "confirmation_id": f"FAM-{parent_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }


@tool
def create_child_account(parent_id: str, child_name: str, year_level: int) -> dict:
    """Create a new child account under an existing parent.

    Year level must be 4-12. Each child gets their own login + progress tracker.
    Returns new student_id + temporary login link (mock).
    """
    if year_level < 4 or year_level > 12:
        return {"error": "Year level must be between 4 and 12"}

    student_id = f"STU-{parent_id[-4:]}-{int(datetime.now().timestamp()) % 100000}"

    return {
        "success": True,
        "parent_id": parent_id,
        "student_id": student_id,
        "child_name": child_name,
        "year_level": year_level,
        "login_email": f"{child_name.lower().replace(' ', '.')}@acmeacademy.com.au",
        "setup_link": f"https://acmeacademy.com.au/setup/{student_id}",
        "next_steps": [
            "Parent receives email with setup link",
            "Child sets own password",
            "Auto-enrolled in family plan benefits if eligible",
        ],
    }


@tool
def escalate_to_teacher(student_id: str, concern: str) -> dict:
    """Flag a student progress concern for review by a human teacher.

    Use when parent expresses worry about progress, performance drops,
    learning difficulties, or anything requiring pedagogical judgement.
    Returns ticket_id and expected response time.
    """
    ticket_id = f"TKT-{student_id[-6:]}-{int(datetime.now().timestamp()) % 100000}"
    return {
        "escalated": True,
        "ticket_id": ticket_id,
        "student_id": student_id,
        "concern_summary": concern[:200],
        "assigned_to": "education_team@acmeacademy.com.au",
        "expected_response_hours": 24,
        "priority": "standard",
    }


@tool
def send_confirmation_email(parent_email: str, action_summary: str) -> dict:
    """Send a confirmation email to the parent (mock — logs only).

    Use after any action that modifies account state (refund, switch, new child).
    """
    return {
        "sent": True,
        "to": parent_email,
        "subject": "Confirmation: action completed",
        "body_preview": action_summary[:140],
        "sent_at": datetime.now().isoformat(),
    }
