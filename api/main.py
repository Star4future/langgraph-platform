"""Vercel serverless entry point — LangGraph Platform demo.

Vercel expects Python functions under the root ``api/`` directory.
This file selects the education vertical for the public demo.
Set ``VERTICAL`` env var on the Vercel project to switch verticals without
redeploying.

No API key required — runs in MOCK_MODE by default (``OPENAI_API_KEY`` unset).
Set ``OPENAI_API_KEY`` on the project to enable real GPT-4o-mini responses.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `core` and `verticals` are importable.
# api/index.py → parent is project root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api import create_app  # noqa: E402  (path must be set first)

# ``VERTICAL`` env var defaults to "education" for the demo.
# Override on your Vercel project settings to deploy a different vertical.
app = create_app(default_vertical=os.getenv("VERTICAL", "education"))
