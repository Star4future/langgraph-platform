"""Resolver Agent base class.

Selects and calls tools, then composes a draft response.
INDUSTRY-AGNOSTIC. Verticals supply tools + prompt.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from core.llm import BaseLLMProvider

logger = logging.getLogger(__name__)


class ResolverAgent:
    """Resolver node: tool-calling + draft generation.

    Each vertical instantiates with its tool list + system prompt.

    Attributes:
        llm:           Provider implementing ``BaseLLMProvider``.
        tools:         Dict of {tool_name: callable} registered for this vertical.
        tool_schemas:  OpenAI-style function schemas for the LLM to choose from.
        system_prompt: Vertical-specific Resolver prompt.
        max_tool_calls: Hard cap on tool invocations per draft.
    """

    def __init__(
        self,
        llm: "BaseLLMProvider",
        tools: dict[str, Callable],
        tool_schemas: list[dict],
        system_prompt: str,
        *,
        max_tool_calls: int = 5,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.tool_schemas = tool_schemas
        self.system_prompt = system_prompt
        self.max_tool_calls = max_tool_calls

    async def __call__(self, state: dict) -> dict:
        """Process state through Resolver.

        Logic:
            1. Send conversation + intent context + tool schemas to LLM.
            2. If LLM requests tool calls, execute and feed results back.
            3. Loop until LLM produces a final draft or max_tool_calls hit.
            4. Return draft_response + tools_called + tool_results.

        Args:
            state: BaseSupportState dict (must have messages + intent).

        Returns:
            Partial state update.
        """
        conversation = self._build_conversation(state)
        tools_called: list[str] = []
        tool_results: dict[str, Any] = {}

        for iteration in range(self.max_tool_calls):
            response = await self.llm.complete(
                messages=conversation,
                tools=self.tool_schemas,
            )

            # Check if LLM wants to call a tool
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                draft = response.get("content", "")
                return {
                    "draft_response": draft,
                    "tools_called": tools_called,
                    "tool_results": tool_results,
                }

            # Execute each tool call
            for call in tool_calls:
                name = call.get("name")
                args = call.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                if name not in self.tools:
                    logger.warning("Unknown tool requested: %s", name)
                    result = {"error": f"Tool '{name}' not available"}
                else:
                    try:
                        result = self.tools[name](**args)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Tool '%s' raised", name)
                        result = {"error": str(exc)}

                tools_called.append(name)
                tool_results[f"{name}:{iteration}"] = result

                # Feed result back using OpenAI v2 tool-call wire format
                call_id = call.get("id", f"call_{iteration}")
                conversation.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": call.get("arguments") if isinstance(call.get("arguments"), str)
                                         else json.dumps(call.get("arguments", {})),
                        },
                    }],
                })
                conversation.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result),
                })

        # Hit max iterations — generate a final response without further tools
        final = await self.llm.complete(messages=conversation, tools=None)
        return {
            "draft_response": final.get("content", "I was unable to complete this request."),
            "tools_called": tools_called,
            "tool_results": tool_results,
        }

    # ── internal helpers ────────────────────────────────────────────

    def _build_conversation(self, state: dict) -> list[dict]:
        """Compose the LLM-facing message list."""
        # System prompt + intent injection
        sys_content = self.system_prompt
        if state.get("intent"):
            sys_content += f"\n\n[Triage classified intent: {state['intent']} (confidence: {state.get('confidence', 0):.2f})]"
        if state.get("quality_feedback"):
            sys_content += f"\n\n[Supervisor feedback on previous draft: {state['quality_feedback']} — please address this.]"

        conversation: list[dict] = [{"role": "system", "content": sys_content}]
        for msg in state.get("messages", []):
            if isinstance(msg, dict):
                conversation.append(msg)
            else:
                # Handle langchain message objects
                role = "user" if getattr(msg, "type", "") in ("human", "user") else "assistant"
                conversation.append({"role": role, "content": getattr(msg, "content", "")})
        return conversation
