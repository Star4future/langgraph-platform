"""Education-specific state extension.

Adds fields used by parent service workflows:
    student_id, parent_id, subscription_id, plan_code, year_level
"""
from __future__ import annotations

from core.state import BaseSupportState


class EducationState(BaseSupportState, total=False):
    """Adds education-specific fields to the base state."""

    # Identity
    parent_id: str | None
    student_id: str | None

    # Subscription
    subscription_id: str | None
    plan_code: str | None         # "M1" | "M3" | "M4" | "M5" | "bundle"

    # Student context
    year_level: int | None        # 4..12
    has_sibling_account: bool


__all__ = ["EducationState"]
