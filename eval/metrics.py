"""Metrics computed by the eval harness.

INDUSTRY-AGNOSTIC. Works for any vertical's 30-scenario dataset.
"""
from __future__ import annotations

import statistics
from typing import Iterable


def compute_metrics(results: list[dict]) -> dict:
    """Compute the 6 standard metrics from a list of per-scenario results.

    Each result dict must contain:
        - "passed": bool
        - "intent_correct": bool
        - "tools_used_correct": bool
        - "human_escalation_correct": bool
        - "quality_score": float (0..1)
        - "retry_count": int
        - "latency_ms": int

    Returns:
        dict with summary metrics + per-category breakdowns.
    """
    if not results:
        return {"error": "No results to score"}

    total = len(results)
    resolved = sum(1 for r in results if r["passed"])
    intent_ok = sum(1 for r in results if r["intent_correct"])
    tools_ok = sum(1 for r in results if r["tools_used_correct"])
    human_ok = sum(1 for r in results if r["human_escalation_correct"])

    quality_scores = [r["quality_score"] for r in results]
    retries = [r["retry_count"] for r in results]
    latencies = sorted(r["latency_ms"] for r in results)

    return {
        "total_scenarios": total,
        "resolution_rate": resolved / total,
        "intent_accuracy": intent_ok / total,
        "tool_choice_accuracy": tools_ok / total,
        "human_escalation_precision": human_ok / total,
        "avg_quality_score": statistics.mean(quality_scores),
        "avg_retry_count": statistics.mean(retries),
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "by_category": _by_category(results),
        "by_difficulty": _by_difficulty(results),
    }


def _percentile(sorted_values: list[int], p: int) -> int:
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    return int(sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f))


def _by_category(results: list[dict]) -> dict:
    out: dict = {}
    for r in results:
        cat = r.get("category", "unknown")
        b = out.setdefault(cat, {"count": 0, "passed": 0})
        b["count"] += 1
        if r["passed"]:
            b["passed"] += 1
    return {
        cat: {**v, "pass_rate": v["passed"] / v["count"] if v["count"] else 0}
        for cat, v in out.items()
    }


def _by_difficulty(results: list[dict]) -> dict:
    out: dict = {}
    for r in results:
        d = r.get("difficulty", "unknown")
        b = out.setdefault(d, {"count": 0, "passed": 0})
        b["count"] += 1
        if r["passed"]:
            b["passed"] += 1
    return {
        d: {**v, "pass_rate": v["passed"] / v["count"] if v["count"] else 0}
        for d, v in out.items()
    }


# ─── Per-scenario judges ──────────────────────────────────────────

def judge_scenario(
    scenario: dict,
    final_state: dict,
    *,
    latency_ms: int,
) -> dict:
    """Compare a single scenario's expectations against the run's final state.

    Returns the dict expected by ``compute_metrics``.
    """
    intent_correct = final_state.get("intent") == scenario["expected_intent"]

    expected_tools = set(scenario.get("expected_tools", []))
    actual_tools = set(final_state.get("tools_called", []))
    # Allow superset (LLM might call extra tools, that's fine)
    tools_used_correct = expected_tools.issubset(actual_tools) if expected_tools else True

    expected_human = scenario.get("should_require_human", False)
    actual_human = (
        final_state.get("requires_human", False)
        or final_state.get("retry_count", 0) >= 2
    )
    human_escalation_correct = expected_human == actual_human

    quality_score = float(final_state.get("quality_score", 0.0))
    quality_pass = quality_score >= scenario.get("quality_threshold", 0.7)

    # PASS criteria: intent correct + tools/escalation routing correct + quality gate
    # NOTE: escalation does NOT auto-pass quality — a bad response that happened to escalate
    # should still be scored on quality.
    passed = (
        intent_correct
        and (tools_used_correct or human_escalation_correct)
        and quality_pass
    )

    return {
        "id": scenario["id"],
        "category": scenario.get("category", "unknown"),
        "difficulty": scenario.get("difficulty", "unknown"),
        "passed": passed,
        "intent_correct": intent_correct,
        "tools_used_correct": tools_used_correct,
        "human_escalation_correct": human_escalation_correct,
        "quality_score": quality_score,
        "retry_count": final_state.get("retry_count", 0),
        "latency_ms": latency_ms,
    }


__all__ = ["compute_metrics", "judge_scenario"]
