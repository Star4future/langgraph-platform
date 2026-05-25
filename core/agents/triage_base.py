"""Triage Agent base class.

Classifies user intent + urgency + decides whether human escalation needed.
INDUSTRY-AGNOSTIC. Verticals provide the prompt + allowed intent list.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.llm import BaseLLMProvider

logger = logging.getLogger(__name__)


class TriageAgent:
    """Triage node: classify intent + extract entities.

    Each vertical instantiates this with its own ``system_prompt``
    (which lists allowed intents) and ``high_risk_keywords`` (which
    force ``requires_human=True``).

    Attributes:
        llm:                 Provider implementing ``BaseLLMProvider``.
        system_prompt:       Vertical-specific Triage prompt.
        allowed_intents:     List of intent strings the vertical recognises.
        confidence_floor:    Below this, route to human escalation.
        high_risk_keywords:  Words in user message that force human path.
    """

    def __init__(
        self,
        llm: "BaseLLMProvider",
        system_prompt: str,
        allowed_intents: list[str],
        *,
        confidence_floor: float = 0.5,
        high_risk_keywords: list[str] | None = None,
    ) -> None:
        self.llm = llm
        self.system_prompt = system_prompt
        self.allowed_intents = allowed_intents
        self.confidence_floor = confidence_floor
        self.high_risk_keywords = [k.lower() for k in (high_risk_keywords or [])]

    async def __call__(self, state: dict) -> dict:
        """Process state through Triage.

        Args:
            state: BaseSupportState dict.

        Returns:
            Partial state update with intent/confidence/urgency/requires_human.
        """
        user_message = self._extract_last_user_message(state)
        triage_payload = await self._call_llm(user_message)

        intent = triage_payload.get("intent", "unknown")
        confidence = float(triage_payload.get("confidence", 0.0))
        urgency = triage_payload.get("urgency", "low")
        requires_human = bool(triage_payload.get("requires_human", False))

        # Defensive validation
        if intent not in self.allowed_intents:
            logger.warning(
                "Triage returned unknown intent '%s' (allowed: %s)",
                intent, self.allowed_intents,
            )
            intent = "unknown"
            confidence = min(confidence, 0.4)

        # Keyword-based escalation override
        if self._matches_high_risk_keyword(user_message):
            requires_human = True

        return {
            "intent": intent,
            "confidence": confidence,
            "urgency": urgency,
            "requires_human": requires_human,
        }

    # ── internal helpers ────────────────────────────────────────────

    @staticmethod
    def _extract_last_user_message(state: dict) -> str:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", None)
            if role in ("user", "human"):
                return msg.get("content") if isinstance(msg, dict) else msg.content
        return ""

    def _matches_high_risk_keyword(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(k in lower for k in self.high_risk_keywords)

    async def _call_llm(self, user_message: str) -> dict[str, Any]:
        """Call the LLM with the Triage prompt and parse JSON response."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        response = await self.llm.complete(
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = response.get("content", "{}")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error("Triage JSON parse failed: %s — raw: %r", exc, raw)
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "urgency": "low",
                "requires_human": True,  # fail safe: escalate to human
            }
