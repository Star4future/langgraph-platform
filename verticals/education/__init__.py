"""Education vertical — AcmeAcademy AU online tutoring platform.

Plug-in module that adapts the core engine to handle parent service
workflows: subscription queries, refunds, plan switches, family discount
application, child account creation, teacher escalation.

EXPORTS:
    VERTICAL: dict consumed by core/api/main.py app factory
"""
from __future__ import annotations

from pathlib import Path

from . import prompts, tools as _tools_mod
from .graph import build_graph
from .state import EducationState

from core.agents import collect_tools_from_module

_VERTICAL_DIR = Path(__file__).parent
_tools_dict, _tool_schemas = collect_tools_from_module(_tools_mod)


VERTICAL: dict = {
    "name": "education",
    "display_name": "Education / Tutoring (AU)",
    "tools": _tools_dict,
    "tool_schemas": _tool_schemas,
    "prompts": {
        "triage": prompts.TRIAGE_PROMPT,
        "resolver": prompts.RESOLVER_PROMPT,
        "supervisor": prompts.SUPERVISOR_PROMPT,
    },
    "allowed_intents": prompts.ALLOWED_INTENTS,
    "high_risk_keywords": prompts.HIGH_RISK_KEYWORDS,
    "state_class": EducationState,
    "build_graph": build_graph,
    "faq_path": str(_VERTICAL_DIR / "data" / "faq.md"),
    "mock_responses_path": str(_VERTICAL_DIR / "data" / "mock_responses.json"),
    "config_path": str(_VERTICAL_DIR / "config.yaml"),
}

__all__ = ["VERTICAL"]
