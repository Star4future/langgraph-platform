"""OpenAI LLM provider.

Real OpenAI API calls. Used when ``OPENAI_API_KEY`` is set.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class OpenAILLMProvider:
    """Wraps :class:`openai.AsyncOpenAI` to match :class:`BaseLLMProvider`."""

    def __init__(self, *, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import AsyncOpenAI  # imported lazily
        self._client = AsyncOpenAI(api_key=api_key, timeout=30.0)
        self._model = model

    async def complete(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        """Single completion. Returns content + tool_calls + usage."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._normalise(messages),
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = tools
        if response_format:
            kwargs["response_format"] = response_format

        response = await self._client.chat.completions.create(**kwargs)

        msg = response.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })

        return {
            "content": msg.content,
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        }

    async def stream(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream tokens. Used by the SSE endpoint for live responses."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._normalise(messages),
            "temperature": 0.2,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "token", "delta": delta.content}
        yield {"type": "done"}

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _normalise(messages: list[dict]) -> list[dict]:
        """Strip ``None`` content fields that langgraph sometimes injects."""
        cleaned = []
        for m in messages:
            if isinstance(m, dict):
                if m.get("content") is None and not m.get("tool_calls"):
                    continue
                cleaned.append(m)
            else:
                cleaned.append(m)
        return cleaned
