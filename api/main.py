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

from fastapi.responses import HTMLResponse, PlainTextResponse

# Ensure the project root is on sys.path so `core` and `verticals` are importable.
# api/main.py → parent is project root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api import create_app  # noqa: E402  (path must be set first)

# ``VERTICAL`` env var defaults to "education" for the demo.
# Override on your Vercel project settings to deploy a different vertical.
app = create_app(default_vertical=os.getenv("VERTICAL", "education"))


# ── Static landing page ─────────────────────────────────────────────
# Vercel serves Python functions but does NOT auto-serve static files for
# Python-only projects, so we route `/` through FastAPI to return the demo page.
_INDEX_HTML_PATH = ROOT / "index.html"
try:
    _INDEX_HTML = _INDEX_HTML_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    _INDEX_HTML = ""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing() -> HTMLResponse:
    if _INDEX_HTML:
        return HTMLResponse(content=_INDEX_HTML)
    return HTMLResponse(
        content="<h1>LangGraph Platform</h1><p>Demo page not bundled. See <a href='/api/docs'>API docs</a>.</p>",
    )


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nAllow: /\n")
