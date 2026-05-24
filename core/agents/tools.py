"""Tool decorator + registry for vertical-defined functions.

Vertical author writes:

    @tool
    def lookup_subscription(user_email: str) -> dict:
        '''Look up a customer's subscription by email.'''
        ...

This decorator extracts an OpenAI-compatible JSON schema from the function
signature + docstring, so vertical authors don't write schemas by hand.

INDUSTRY-AGNOSTIC.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints


def tool(func: Callable) -> Callable:
    """Mark a function as an LLM-callable tool.

    Adds attributes to the function:
        ._is_tool        = True
        ._tool_schema    = OpenAI-style function schema (dict)
        ._tool_name      = function name

    The vertical's ``tools.py`` should expose a ``TOOLS`` list
    (collected automatically by ``collect_tools_from_module``).

    Args:
        func: Python function with type hints + docstring.

    Returns:
        The same function, with tool metadata attached.
    """
    func._is_tool = True              # type: ignore[attr-defined]
    func._tool_name = func.__name__   # type: ignore[attr-defined]
    func._tool_schema = _build_schema(func)  # type: ignore[attr-defined]
    return func


def collect_tools_from_module(module) -> tuple[dict[str, Callable], list[dict]]:
    """Find all @tool functions in a module.

    Returns:
        (tools_dict, schemas_list) where:
          tools_dict = {name: callable}
          schemas_list = [openai_schema, ...]
    """
    tools: dict[str, Callable] = {}
    schemas: list[dict] = []

    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and getattr(obj, "_is_tool", False):
            tools[obj._tool_name] = obj
            schemas.append(obj._tool_schema)

    return tools, schemas


# ─────────────────────────────────────────────────────────────────────
# internal
# ─────────────────────────────────────────────────────────────────────

_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _build_schema(func: Callable) -> dict[str, Any]:
    """Convert a typed Python function to OpenAI function-calling schema."""
    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties: dict[str, dict] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        annotation = hints.get(param_name, str)
        properties[param_name] = {
            "type": _PY_TO_JSON.get(annotation, "string"),
            "description": "",  # vertical author can extend; default empty
        }
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip().split("\n")[0],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


__all__ = ["tool", "collect_tools_from_module"]
