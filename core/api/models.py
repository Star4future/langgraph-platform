"""Pydantic request/response models for the platform API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ─── Request models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """POST /api/chat — start or continue a conversation."""

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=128)
    customer_id: str = Field(default="anonymous", max_length=128)
    vertical: str | None = Field(
        default=None,
        description="Override default vertical. Optional.",
    )


class ResumeRequest(BaseModel):
    """POST /api/resume — resume a paused (human-in-the-loop) graph."""

    session_id: str
    human_decision: str = Field(..., min_length=1, max_length=4000)


class EvalRequest(BaseModel):
    """POST /api/eval — run a vertical's eval harness."""

    vertical: str
    dataset: str | None = None


# ─── Response models ───────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    mode: Literal["mock", "real"]
    loaded_verticals: list[str]
    default_vertical: str
    config: dict[str, Any]


class PendingItem(BaseModel):
    session_id: str
    customer_id: str
    intent: str
    awaiting_since: str
    summary: str


class PendingHumanResponse(BaseModel):
    pending: list[PendingItem]
    count: int
