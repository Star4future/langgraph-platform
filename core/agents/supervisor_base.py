"""Supervisor Agent base class.

Quality-gates the Resolver's draft. Returns to Resolver if score < threshold.
INDUSTRY-AGNOSTIC. Verticals supply scoring prompt + threshold.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.llm import BaseLLMProvider

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """Supervisor node: rate draft quality + decide pass/retry.

    Each vertical configures its scoring prompt + threshold.

    Attributes:
        llm:                Provider implementing ``BaseLLMProvider``.
        system_prompt:      Vertical-specific Supervisor prompt.
        quality_threshold:  Min score for PASS (typically 0.7).
    """

    def __init__(
        self,
        llm: "BaseLLMProvider",
        system_prompt: str,
        *,
        quality_threshold: float = 0.7,
    ) -> None:
        self.llm = llm
        self.system_prompt = system_prompt
        self.quality_threshold = quality_threshold

    async def __call__(self, state: dict) -> dict:
        """Process state through Supervisor.

        Args:
            state: BaseSupportState dict (must have draft_response + tools_called).

        Returns:
            Partial state update with quality_score / quality_feedback / final_response / retry_count.
        """
        draft = state.get("draft_response", "")
        if not draft:
            # Nothing to score — fail fast, escalate
            return {
                "quality_score": 0.0,
                "quality_feedback": "Resolver produced no draft.",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        user_msg = self._extract_last_user_message(state)
        verdict = await self._call_llm(
            user_message=user_msg,
            draft=draft,
            tools_called=state.get("tools_called", []),
            tool_results=state.get("tool_results", {}),
            intent=state.get("intent", "unknown"),
        )

        score = float(verdict.get("quality_score", 0.0))
        passes = score >= self.quality_threshold
        feedback = verdict.get("feedback", "")

        update: dict[str, Any] = {
            "quality_score": score,
            "quality_feedback": feedback,
        }
        if passes:
            update["final_response"] = draft
            update["resolved"] = True
            # Append assistant reply to messages so multi-turn conversations retain context
            update["messages"] = [{"role": "assistant", "content": draft}]
        else:
            update["retry_count"] = state.get("retry_count", 0) + 1

        return update

    # ── internal helpers ────────────────────────────────────────────

    @staticmethod
    def _extract_last_user_message(state: dict) -> str:
        for msg in reversed(state.get("messages", [])):
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", None)
            if role in ("user", "human"):
                return msg.get("content") if isinstance(msg, dict) else msg.content
        return ""

    async def _call_llm(
        self,
        *,
        user_message: str,
        draft: str,
        tools_called: list[str],
        tool_results: dict,
        intent: str,
    ) -> dict[str, Any]:
        review_input = (
            f"User question: {user_message}\n\n"
            f"Triage intent: {intent}\n\n"
            f"Tools used: {', '.join(tools_called) or 'none'}\n\n"
            f"Tool results (truncated): {json.dumps(tool_results)[:1000]}\n\n"
            f"Draft response to evaluate:\n{draft}\n\n"
            f"Score this draft 0..1 on accuracy, tone, completeness, safety. "
            f"Return JSON: {{\"quality_score\": float, \"passes\": bool, \"feedback\": str}}"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": review_input},
        ]
        response = await self.llm.complete(
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = response.get("content", "{}")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error("Supervisor JSON parse failed: %s — raw: %r", exc, raw)
            # Fail with low score so Resolver retries rather than silently passing
            return {"quality_score": 0.0, "passes": False, "feedback": "Supervisor response unparseable — retrying."}
