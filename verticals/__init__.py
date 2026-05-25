"""Vertical registry.

Each vertical is a directory exporting a ``VERTICAL`` dict.
Verticals MUST NOT import from each other or from ``core.api``.

Adding a new vertical:
    1. ``cp -r verticals/_template verticals/<industry>``
    2. Fill in the 6 required files (see VERTICAL-AUTHORING-GUIDE.md)
    3. Import + register it here
"""
from __future__ import annotations

from .education import VERTICAL as education_vertical

VERTICALS: dict[str, dict] = {
    "education": education_vertical,
    # "insurance": insurance_vertical,  # ← add here after authoring
    # "ecommerce": ecommerce_vertical,
}


def get_vertical(name: str) -> dict:
    """Look up a registered vertical by name.

    Args:
        name: Industry name (e.g. "education", "insurance").

    Returns:
        VERTICAL dict containing tools / prompts / state / graph builder.

    Raises:
        KeyError: If the vertical is not registered.
    """
    if name not in VERTICALS:
        raise KeyError(
            f"Vertical '{name}' not registered. "
            f"Available: {list(VERTICALS.keys())}. "
            f"See VERTICAL-AUTHORING-GUIDE.md to add a new vertical."
        )
    return VERTICALS[name]


__all__ = ["VERTICALS", "get_vertical"]
