"""Assemble the education vertical's LangGraph.

Wires Triage + Resolver + Supervisor with education-specific prompts and tools.
Called by core/api/main.py via the VERTICAL dict's ``build_graph`` key.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from core.agents import ResolverAgent, SupervisorAgent, TriageAgent, collect_tools_from_module
from core.checkpointing import build_checkpointer
from core.graph_builder import build_support_graph
from core.llm import get_llm_provider

from . import prompts, tools as _tools_module
from .state import EducationState


_VERTICAL_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def _load_config() -> dict:
    """Load config.yaml (cached for process lifetime)."""
    with open(_VERTICAL_DIR / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def build_graph():
    """Build and return a compiled LangGraph for the education vertical.

    Cached — same compiled graph instance reused across requests (per process).
    """
    config = _load_config()

    # ── Vertical config for LLM provider (so mock can find mock_responses.json) ──
    vertical_config = {
        "name": "education",
        "mock_responses_path": str(_VERTICAL_DIR / "data" / "mock_responses.json"),
    }
    llm = get_llm_provider(vertical_config)

    # ── Tool collection ─────────────────────────────────────────────
    tools_dict, tool_schemas = collect_tools_from_module(_tools_module)

    # ── Behavioural knobs (env overrides config defaults) ───────────
    quality_threshold = float(
        os.getenv(
            "QUALITY_THRESHOLD",
            str(config["business_rules"]["quality_threshold"]),
        )
    )
    max_retries = int(
        os.getenv(
            "MAX_RETRY_COUNT",
            str(config["business_rules"]["max_retry_count"]),
        )
    )
    confidence_floor = float(
        os.getenv(
            "TRIAGE_CONFIDENCE_FLOOR",
            str(config["business_rules"]["triage_confidence_floor"]),
        )
    )

    # ── Agent instantiation ─────────────────────────────────────────
    triage = TriageAgent(
        llm=llm,
        system_prompt=prompts.TRIAGE_PROMPT,
        allowed_intents=prompts.ALLOWED_INTENTS,
        confidence_floor=confidence_floor,
        high_risk_keywords=prompts.HIGH_RISK_KEYWORDS,
    )
    resolver = ResolverAgent(
        llm=llm,
        tools=tools_dict,
        tool_schemas=tool_schemas,
        system_prompt=prompts.RESOLVER_PROMPT,
        max_tool_calls=5,
    )
    supervisor = SupervisorAgent(
        llm=llm,
        system_prompt=prompts.SUPERVISOR_PROMPT,
        quality_threshold=quality_threshold,
    )

    # ── Build graph ─────────────────────────────────────────────────
    return build_support_graph(
        state_class=EducationState,
        triage=triage,
        resolver=resolver,
        supervisor=supervisor,
        quality_threshold=quality_threshold,
        max_retries=max_retries,
        confidence_floor=confidence_floor,
        checkpointer=build_checkpointer(),
    )


__all__ = ["build_graph"]
