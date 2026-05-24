"""LLM provider adapters (mock + openai)."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .base import BaseLLMProvider
from .mock import MockLLMProvider

if TYPE_CHECKING:
    from .openai_client import OpenAILLMProvider


def get_llm_provider(vertical_config: dict | None = None) -> BaseLLMProvider:
    """Return the appropriate LLM provider based on environment.

    MOCK_MODE (no OPENAI_API_KEY) -> MockLLMProvider using vertical mock_responses
    Real mode -> OpenAILLMProvider using gpt-4o-mini by default

    Args:
        vertical_config: dict from a vertical containing 'mock_responses_path'
                         and 'name'; required for MockLLMProvider.

    Returns:
        BaseLLMProvider implementation.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or "xxxxx" in api_key:
        from .mock import MockLLMProvider
        return MockLLMProvider.from_vertical(vertical_config or {})
    from .openai_client import OpenAILLMProvider
    return OpenAILLMProvider(
        api_key=api_key,
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )


__all__ = ["BaseLLMProvider", "MockLLMProvider", "get_llm_provider"]
