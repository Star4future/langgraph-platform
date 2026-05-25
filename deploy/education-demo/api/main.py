"""Vercel entry point for the AcmeAcademy deployment.

Uses the platform's ``core.api.create_app`` factory + selects the
education vertical. Vercel auto-detects this as a Python serverless
function via the .py extension.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ─── Project root on sys.path ──────────────────────────────────────
# deploy/education-demo/api/main.py → ../../../ is project root
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api import create_app

app = create_app(default_vertical="education")
