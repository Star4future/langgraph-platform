"""Run an eval for a given vertical against its scenario dataset.

Usage (CLI):
    python -m eval.run_eval --vertical education
    python -m eval.run_eval --vertical education --dataset eval/datasets/education_30.jsonl

Outputs:
    eval/results/<vertical>_<timestamp>.json
    eval/EVAL-RESULTS.md   (overwrites with latest)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.state import initial_state
from eval.metrics import compute_metrics, judge_scenario

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("eval")


async def run_evaluation(
    *,
    vertical_name: str,
    dataset_path: str | None = None,
) -> dict:
    """Run the eval and return metrics."""
    from verticals import get_vertical

    vertical = get_vertical(vertical_name)

    if dataset_path is None:
        dataset_path = str(ROOT / "eval" / "datasets" / f"{vertical_name}_30.jsonl")

    scenarios = _load_dataset(dataset_path)
    logger.info("Loaded %d scenarios from %s", len(scenarios), dataset_path)

    graph = vertical["build_graph"]()

    results = []
    for scenario in scenarios:
        t_start = time.time()
        state = initial_state(
            session_id=f"eval_{scenario['id']}",
            customer_id="eval_runner",
            user_message=scenario["input"],
            vertical_name=vertical_name,
            mode="mock",
        )

        try:
            # Use ainvoke for synchronous evaluation
            config = {"configurable": {"thread_id": f"eval_{scenario['id']}"}}
            final_state = await graph.ainvoke(state, config=config)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scenario %s failed: %s", scenario["id"], exc)
            final_state = state

        latency = int((time.time() - t_start) * 1000)
        result = judge_scenario(scenario, final_state, latency_ms=latency)
        results.append(result)

        marker = "✓" if result["passed"] else "✗"
        logger.info(
            "%s %s [%s/%s] intent=%s quality=%.2f tools=%d retries=%d",
            marker,
            scenario["id"],
            result["category"],
            result["difficulty"],
            "ok" if result["intent_correct"] else "wrong",
            result["quality_score"],
            int(result["tools_used_correct"]),
            result["retry_count"],
        )

    metrics = compute_metrics(results)

    # Save artefacts
    _save_results(vertical_name, results, metrics)
    _write_report(vertical_name, metrics, results, dataset_path)

    return metrics


def _load_dataset(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    scenarios = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("//"):
                scenarios.append(json.loads(line))
    return scenarios


def _save_results(vertical_name: str, results: list[dict], metrics: dict) -> Path:
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{vertical_name}_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "results": results, "timestamp": ts}, f, indent=2)
    logger.info("Wrote %s", out_path)
    return out_path


def _write_report(vertical_name: str, metrics: dict, results: list[dict], dataset_path: str) -> Path:
    report_path = ROOT / "eval" / "EVAL-RESULTS.md"
    md = _format_report(vertical_name, metrics, results, dataset_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    logger.info("Wrote %s", report_path)
    return report_path


def _format_report(vertical_name: str, metrics: dict, results: list[dict], dataset_path: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Eval Results — `{vertical_name}` vertical",
        "",
        f"**Dataset:** `{dataset_path}` ({metrics['total_scenarios']} scenarios)",
        f"**Mode:** MOCK_MODE (deterministic, no LLM cost)",
        f"**Run at:** {ts}",
        "",
        "## Summary metrics",
        "",
        "| Metric | Value | Threshold | Status |",
        "|--------|-------|-----------|--------|",
        f"| Resolution rate | {metrics['resolution_rate']:.0%} | ≥ 70% | {_status(metrics['resolution_rate'], 0.70)} |",
        f"| Intent accuracy | {metrics['intent_accuracy']:.0%} | ≥ 85% | {_status(metrics['intent_accuracy'], 0.85)} |",
        f"| Tool choice accuracy | {metrics['tool_choice_accuracy']:.0%} | ≥ 80% | {_status(metrics['tool_choice_accuracy'], 0.80)} |",
        f"| Human escalation precision | {metrics['human_escalation_precision']:.0%} | ≥ 90% | {_status(metrics['human_escalation_precision'], 0.90)} |",
        f"| Avg quality score | {metrics['avg_quality_score']:.2f} | ≥ 0.70 | {_status(metrics['avg_quality_score'], 0.70)} |",
        f"| Avg retry count | {metrics['avg_retry_count']:.2f} | ≤ 0.5 | {_status_inverse(metrics['avg_retry_count'], 0.5)} |",
        f"| Latency P50 | {metrics['latency_p50_ms']} ms | ≤ 3000 | {_status_inverse(metrics['latency_p50_ms'], 3000)} |",
        f"| Latency P95 | {metrics['latency_p95_ms']} ms | ≤ 6000 | {_status_inverse(metrics['latency_p95_ms'], 6000)} |",
        "",
        "## By category",
        "",
        "| Category | Count | Passed | Rate |",
        "|----------|-------|--------|------|",
    ]
    for cat, b in sorted(metrics["by_category"].items()):
        lines.append(f"| {cat} | {b['count']} | {b['passed']} | {b['pass_rate']:.0%} |")

    lines.extend([
        "",
        "## By difficulty",
        "",
        "| Difficulty | Count | Passed | Rate |",
        "|------------|-------|--------|------|",
    ])
    for d, b in sorted(metrics["by_difficulty"].items()):
        lines.append(f"| {d} | {b['count']} | {b['passed']} | {b['pass_rate']:.0%} |")

    lines.extend([
        "",
        "## Per-scenario results",
        "",
        "| ID | Category | Difficulty | Pass | Intent | Tools | Human | Quality | Latency |",
        "|----|----------|------------|------|--------|-------|-------|---------|---------|",
    ])
    for r in results:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['difficulty']} | "
            f"{'✓' if r['passed'] else '✗'} | "
            f"{'✓' if r['intent_correct'] else '✗'} | "
            f"{'✓' if r['tools_used_correct'] else '✗'} | "
            f"{'✓' if r['human_escalation_correct'] else '✗'} | "
            f"{r['quality_score']:.2f} | {r['latency_ms']} ms |"
        )

    return "\n".join(lines) + "\n"


def _status(value: float, threshold: float) -> str:
    return "✓ PASS" if value >= threshold else "✗ FAIL"


def _status_inverse(value: float, threshold: float) -> str:
    return "✓ PASS" if value <= threshold else "✗ FAIL"


# ─── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run vertical eval harness")
    parser.add_argument("--vertical", required=True, help="Vertical name (e.g. education)")
    parser.add_argument("--dataset", default=None, help="Path to JSONL dataset")
    args = parser.parse_args()

    metrics = asyncio.run(
        run_evaluation(vertical_name=args.vertical, dataset_path=args.dataset)
    )

    print("\n=== EVAL SUMMARY ===")
    for k in ("resolution_rate", "intent_accuracy", "human_escalation_precision", "avg_quality_score"):
        print(f"  {k:35s} {metrics[k]:.2f}")

    gate = metrics["resolution_rate"] >= 0.70
    print(f"\nCI gate (resolution_rate >= 0.70): {'PASS ✓' if gate else 'FAIL ✗'}")
    sys.exit(0 if gate else 1)


if __name__ == "__main__":
    main()
