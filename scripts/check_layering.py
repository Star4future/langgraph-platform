"""Layering gate — verify that core/ contains no industry-specific identifiers.

Usage:
    python scripts/check_layering.py           # delegates to pytest (recommended)
    python scripts/check_layering.py --standalone  # run without pytest

Exit codes:
    0  — All checks pass (core is industry-agnostic)
    1  — Violations found; details printed to stdout

This script is the CLI wrapper around the pytest-based test in
tests/test_layering.py.  Run it in CI or as a pre-commit check before shipping
a new vertical to confirm no business keywords leaked into the shared engine.

The authoritative ruleset lives in ``tests/test_layering.py``.  The standalone
mode below mirrors those rules exactly.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── Authoritative keyword set (must match tests/test_layering.py exactly) ────
INDUSTRY_KEYWORDS = {
    "aceachievers",
    "AMC", "AIMO",
    "parent_id", "student_id",
    "policy_id", "claim_id", "premium_id",
    "order_id", "shipping_id",
    "patient_id", "appointment_id",
}

CORE_DIR = ROOT / "core"


def _is_docstring(node: ast.Constant, tree: ast.AST) -> bool:
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if parent.body and isinstance(parent.body[0], ast.Expr):
                first = parent.body[0]
                if isinstance(first.value, ast.Constant) and first.value is node:
                    return True
    return False


def run_standalone() -> int:
    """Standalone mode — no pytest required."""
    offenders: list[tuple[str, int, str]] = []
    py_files = sorted(CORE_DIR.rglob("*.py"))

    for py in py_files:
        source = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in INDUSTRY_KEYWORDS:
                    offenders.append((str(py.relative_to(ROOT)), node.lineno, node.id))
            elif isinstance(node, ast.Attribute):
                if node.attr in INDUSTRY_KEYWORDS:
                    offenders.append((str(py.relative_to(ROOT)), node.lineno, node.attr))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _is_docstring(node, tree):
                    continue
                lower = node.value.lower()
                for kw in INDUSTRY_KEYWORDS:
                    if lower == kw.lower():
                        offenders.append((str(py.relative_to(ROOT)), node.lineno, kw))

    if offenders:
        print(f"FAIL — {len(offenders)} layering violation(s) in core/:\n")
        for f, ln, kw in offenders:
            print(f"  {f}:{ln}  '{kw}'")
        print("\nFix: move industry-specific logic into the appropriate vertical.")
        return 1

    print(f"PASS — {len(py_files)} files in core/ are industry-agnostic.")
    return 0


def main() -> int:
    if "--standalone" in sys.argv:
        return run_standalone()

    # Prefer pytest for richer output and test discoverability
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_layering.py", "-v"],
            cwd=str(ROOT),
        )
        return result.returncode
    except FileNotFoundError:
        print("pytest not found — running in standalone mode")
        return run_standalone()


if __name__ == "__main__":
    sys.exit(main())
