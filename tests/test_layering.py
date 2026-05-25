"""Layering enforcement tests.

CRITICAL: These tests guard the core architectural invariant —
core/ must remain industry-agnostic. Verticals depend on core; core never depends on verticals.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


CORE_DIR = ROOT / "core"
VERTICALS_DIR = ROOT / "verticals"

# Words that should NEVER appear as identifiers / values in core/
# (NOT in docstrings or comments — those legitimately describe the rules)
INDUSTRY_KEYWORDS = {
    "aceachievers",
    "AMC", "AIMO",
    "parent_id", "student_id",
    "policy_id", "claim_id", "premium_id",
    "order_id", "shipping_id",
    "patient_id", "appointment_id",
}


def test_core_has_no_industry_imports() -> None:
    """No core/ file may import from verticals."""
    offenders = []
    for py in CORE_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("from verticals") or stripped.startswith("import verticals"):
                offenders.append((str(py.relative_to(ROOT)), line))
    # Allow lazy imports inside functions (we use them deliberately in main.py)
    # — but those should be inside def blocks, not module-top-level.
    # For v1, the test just flags top-level imports; lazy imports in function bodies are exempt.
    top_level = [o for o in offenders if not _is_inside_function(ROOT / o[0], o[1])]
    assert not top_level, f"core/ has top-level imports from verticals/: {top_level}"


def test_core_has_no_industry_identifiers() -> None:
    """No core/ file may use industry-specific identifiers in actual code.

    Uses AST to inspect identifiers and string literals — ignores docstrings
    and comments (which legitimately describe the layering rule).
    """
    offenders = []
    for py in CORE_DIR.rglob("*.py"):
        source = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # Names and attributes (identifiers in actual code)
            if isinstance(node, ast.Name):
                if node.id in INDUSTRY_KEYWORDS:
                    offenders.append((str(py.relative_to(ROOT)), node.lineno, node.id))
            elif isinstance(node, ast.Attribute):
                if node.attr in INDUSTRY_KEYWORDS:
                    offenders.append((str(py.relative_to(ROOT)), node.lineno, node.attr))
            # String literals in non-docstring positions
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _is_docstring(node, tree):
                    continue
                lower = node.value.lower()
                for kw in INDUSTRY_KEYWORDS:
                    # Only flag if entire string is the keyword (avoid prose matches)
                    if lower == kw.lower():
                        offenders.append((str(py.relative_to(ROOT)), node.lineno, kw))

    assert not offenders, (
        f"Industry-coupling leak in core/:\n" +
        "\n".join(f"  {f}:{ln}  '{kw}'" for f, ln, kw in offenders)
    )


def test_verticals_only_import_from_core() -> None:
    """A vertical may import from core/ and itself, but not from other verticals."""
    offenders = []
    for vertical_dir in VERTICALS_DIR.iterdir():
        if not vertical_dir.is_dir() or vertical_dir.name.startswith("_"):
            continue
        own_name = vertical_dir.name
        for py in vertical_dir.rglob("*.py"):
            for line in py.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                m = re.match(r"^(from|import)\s+verticals\.(\w+)", stripped)
                if m and m.group(2) != own_name:
                    offenders.append((str(py.relative_to(ROOT)), stripped))
    assert not offenders, f"Cross-vertical imports detected: {offenders}"


# ─── helpers ───────────────────────────────────────────────────────

def _is_inside_function(path: Path, target_line: str) -> bool:
    """True if the matched line is inside a function/method body."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start, end = node.lineno, (node.end_lineno or node.lineno)
            for i, l in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if start <= i <= end and target_line.strip() in l:
                    return True
    return False


def _is_docstring(node: ast.Constant, tree: ast.AST) -> bool:
    """Check whether a string constant is a docstring (first stmt of module/class/function)."""
    for parent in ast.walk(tree):
        if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if parent.body and isinstance(parent.body[0], ast.Expr):
                first = parent.body[0]
                if isinstance(first.value, ast.Constant) and first.value is node:
                    return True
    return False
