"""Mock LLM provider.

Deterministic LLM substitute for MOCK_MODE + tests.
Verticals supply a ``mock_responses.json`` mapping keyword triggers to
canned LLM behaviour (intent classifications, tool calls, draft responses).

INDUSTRY-AGNOSTIC. The provider knows nothing about education / insurance / etc.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class MockLLMProvider:
    """LLM provider that returns canned vertical-specified responses.

    Scenario JSON structure (per vertical):
        [
          {
            "keywords": ["refund", "money back"],
            "stage": "triage" | "resolver" | "supervisor" | "any",
            "intent": "refund_request",
            "confidence": 0.92,
            "urgency": "medium",
            "requires_human": false,
            "tool_calls": [{"name": "check_refund_eligibility", "arguments": {...}}],
            "response": "Markdown response text",
            "quality_score": 0.85,
            "feedback": "..."
          },
          ...
        ]
    """

    def __init__(self, scenarios: list[dict] | None = None) -> None:
        self.scenarios: list[dict] = scenarios or []

    # ── construction ────────────────────────────────────────────────

    @classmethod
    def from_vertical(cls, vertical_config: dict) -> "MockLLMProvider":
        """Load scenarios from the vertical's mock_responses.json.

        Args:
            vertical_config: Vertical dict — looks up
                             vertical_config['mock_responses_path']
                             relative to project root.

        Returns:
            MockLLMProvider with scenarios loaded (empty list if file missing).
        """
        path = vertical_config.get("mock_responses_path")
        if not path:
            logger.warning("Vertical has no mock_responses_path; returning empty mock")
            return cls([])

        p = Path(path)
        if not p.exists():
            logger.warning("Mock scenarios file not found: %s", p)
            return cls([])

        with open(p, encoding="utf-8") as f:
            scenarios = json.load(f)
        logger.info("Loaded %d mock scenarios from %s", len(scenarios), p)
        return cls(scenarios)

    # ── completion ──────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        """Match user message to a scenario; return canned response.

        Branching:
            - If response_format is JSON (Triage/Supervisor), return JSON content.
            - Otherwise (Resolver), return content + optional tool_calls.
        """
        user_text = self._extract_user_text(messages)
        sys_text = self._extract_system_text(messages)
        stage = self._infer_stage(sys_text, tools, response_format)
        scenario = self._match_scenario(user_text, stage)

        await asyncio.sleep(0.05)  # simulate latency

        if response_format and response_format.get("type") == "json_object":
            # Triage or Supervisor expects JSON
            if stage == "triage":
                payload = {
                    "intent": scenario.get("intent", "general"),
                    "confidence": scenario.get("confidence", 0.7),
                    "urgency": scenario.get("urgency", "low"),
                    "requires_human": scenario.get("requires_human", False),
                }
            elif stage == "supervisor":
                payload = {
                    "quality_score": scenario.get("quality_score", 0.8),
                    "passes": scenario.get("quality_score", 0.8) >= 0.7,
                    "feedback": scenario.get("feedback", "Looks good."),
                }
            else:
                payload = {}
            return {"content": json.dumps(payload), "tool_calls": [], "usage": {}}

        # Resolver path
        tool_calls = []
        # If tools provided and scenario has tool_calls, simulate a tool-call round
        if tools and scenario.get("tool_calls") and not self._has_tool_results(messages):
            tool_calls = [
                {
                    "id": f"call_{i}_{random.randint(1000, 9999)}",
                    "name": tc["name"],
                    "arguments": json.dumps(tc.get("arguments", {})),
                }
                for i, tc in enumerate(scenario["tool_calls"])
            ]
            return {"content": None, "tool_calls": tool_calls, "usage": {}}

        return {
            "content": scenario.get("response", self._fallback_response()),
            "tool_calls": [],
            "usage": {},
        }

    async def stream(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream the matched scenario's response token-by-token."""
        user_text = self._extract_user_text(messages)
        scenario = self._match_scenario(user_text, "resolver")
        text = scenario.get("response", self._fallback_response())

        words = text.split(" ")
        for i in range(0, len(words), 4):
            chunk = " ".join(words[i:i + 4])
            if i + 4 < len(words):
                chunk += " "
            yield {"type": "token", "delta": chunk}
            await asyncio.sleep(0.04)
        yield {"type": "done"}

    # ── internal ────────────────────────────────────────────────────

    def _match_scenario(self, user_text: str, stage: str) -> dict:
        """Best-effort keyword match. Falls back to generic."""
        lower = (user_text or "").lower()
        for s in self.scenarios:
            if stage not in (s.get("stage", "any"), "any") and s.get("stage", "any") != "any":
                continue
            if any(k in lower for k in s.get("keywords", [])):
                return s
        return self.scenarios[-1] if self.scenarios else {}

    @staticmethod
    def _extract_user_text(messages: list[dict]) -> str:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") in ("user", "human"):
                return msg.get("content", "")
        return ""

    @staticmethod
    def _extract_system_text(messages: list[dict]) -> str:
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                return msg.get("content", "")
        return ""

    @staticmethod
    def _has_tool_results(messages: list[dict]) -> bool:
        return any(
            isinstance(m, dict) and m.get("role") == "tool"
            for m in messages
        )

    @staticmethod
    def _infer_stage(sys_text: str, tools, response_format) -> str:
        if response_format and response_format.get("type") == "json_object":
            if "triage" in sys_text.lower():
                return "triage"
            if "supervisor" in sys_text.lower() or "quality" in sys_text.lower():
                return "supervisor"
        return "resolver"

    @staticmethod
    def _fallback_response() -> str:
        return (
            "Thanks for your question. Let me check our help articles for the best answer.\n\n"
            "If you need a quick response, our team is reachable via the contact form on our website."
        )
