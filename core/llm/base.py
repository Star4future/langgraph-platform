"""LLM provider adapter protocol.

All LLM providers (mock, openai, anthropic, etc.) implement this protocol.
The rest of the code only talks to the protocol — providers are swappable
via environment configuration.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Protocol


class BaseLLMProvider(Protocol):
    """Protocol every LLM provider must implement."""

    async def complete(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        """Run a single completion.

        Args:
            messages:        OpenAI-style messages list.
            tools:           Optional list of tool schemas for function calling.
            response_format: Optional response format spec (e.g. {"type": "json_object"}).

        Returns:
            {"content": str | None, "tool_calls": list[dict], "usage": dict}
        """
        ...

    async def stream(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream a completion token-by-token.

        Yields:
            Event dicts: {"type": "token", "delta": str} or
                         {"type": "tool_call", ...} or
                         {"type": "done"}
        """
        ...
