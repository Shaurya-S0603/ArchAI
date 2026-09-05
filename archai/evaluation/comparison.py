"""Phase 2B candidate-versus-baseline comparison and promotion gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from archai.evaluation.benchmark import evaluate_benchmark
from archai.evaluation.candidates import (
    DETERMINISTIC_BASELINE_NAME,
    SOLVER_CANDIDATE_NAME,
    get_candidate,
)
from archai.evaluation.dataset import load_benchmark
from archai.version import VERSION

MINIMUM_ADJACENCY_GAIN = 0.05
MINIMUM_DIVERSITY = 0.08
MAXIMUM_BUDGET_REGRESSION = 0.01
MAXIMUM_ALIGNMENT_REGRESSION = 0.01


def compare_reports(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    if baseline["dataset_sha256"] != candidate["dataset_sha256"]:
        raise ValueError("Candidate reports must use the same benchmark dataset.")

    baseline_summary = baseline["summary"]
    candidate_summary = candidate["summary"]
    deltas = {
        metric: round(candidate_summary[metric] - baseline_summary[metric], 4)
        for metric in (
            "case_success_rate",
            "concept_count_pass_rate",
            "hard_constraint_pass_rate",
            "program_match_rate",
            "mean_adjacency_satisfaction",
            "mean_diversity_score",
            "budget_fit_rate",
            "mean_accessibility_score",
            "mean_user_alignment_score",
        )
    }
    gates = {
        "candidate_regression_gates": {
            "actual": candidate["passed"],
            "required": True,
            "passed": candidate["passed"],
        },
        "adjacency_gain": {
            "actual": deltas["mean_adjacency_satisfaction"],
            "minimum": MINIMUM_ADJACENCY_GAIN,
            "passed": deltas["mean_adjacency_satisfaction"] >= MINIMUM_ADJACENCY_GAIN,
        },
        "candidate_diversity": {
            "actual": candidate_summary["mean_diversity_score"],
            "minimum": MINIMUM_DIVERSITY,
            "passed": candidate_summary["mean_diversity_score"] >= MINIMUM_DIVERSITY,
        },
        "budget_regression": {
            "actual": deltas["budget_fit_rate"],
            "minimum": -MAXIMUM_BUDGET_REGRESSION,
            "passed": deltas["budget_fit_rate"] >= -MAXIMUM_BUDGET_REGRESSION,
        },
        "alignment_regression": {
            "actual": deltas["mean_user_alignment_score"],
            "minimum": -MAXIMUM_ALIGNMENT_REGRESSION,
            "passed": deltas["mean_user_alignment_score"] >= -MAXIMUM_ALIGNMENT_REGRESSION,
        },
    }
    return {
        "comparison_schema_version": 1,
        "application_version": VERSION,
        "dataset_sha256": baseline["dataset_sha256"],
        "baseline": {
            "candidate": baseline["candidate"],
            "summary": baseline_summary,
        },
        "candidate": {
            "candidate": candidate["candidate"],
            "summary": candidate_summary,
        },
        "deltas": deltas,
        "gates": gates,
        "passed": all(gate["passed"] for gate in gates.values()),
    }


def comparison_to_markdown(comparison: dict[str, Any]) -> str:
    baseline = comparison["baseline"]["summary"]
    candidate = comparison["candidate"]["summary"]
    deltas = comparison["deltas"]
    metrics = (
        ("Generation success", "case_success_rate", True),
        ("Five-concept contract", "concept_count_pass_rate", True),
        ("Hard-constraint pass", "hard_constraint_pass_rate", True),
        ("Room-program match", "program_match_rate", True),
        ("Adjacency satisfaction", "mean_adjacency_satisfaction", True),
        ("Concept diversity", "mean_diversity_score", False),
        ("Budget fit", "budget_fit_rate", True),
        ("Accessibility alignment", "mean_accessibility_score", True),
        ("User alignment", "mean_user_alignment_score", True),
    )

    lines = [
        "# ArchAI Phase 2B Candidate Comparison",
        "",
        f"- Application: `{comparison['application_version']}`",
        f"- Baseline: `{comparison['baseline']['candidate']}`",
        f"- Candidate: `{comparison['candidate']['candidate']}`",
        f"- Dataset SHA-256: `{comparison['dataset_sha256']}`",
        f"- Promotion gate: **{'PASS' if comparison['passed'] else 'FAIL'}**",
        "",
        "## Metrics",
        "",
        "| Metric | Baseline | Candidate | Delta |",
        "|---|---:|---:|---:|",
    ]
    for label, metric, percentage in metrics:
        formatter = ".1%" if percentage else ".4f"
        lines.append(
            f"| {label} | {baseline[metric]:{formatter}} | "
            f"{candidate[metric]:{formatter}} | {deltas[metric]:+{formatter}} |"
        )

    lines.extend(
        [
            "",
            "## Promotion gates",
            "",
            "| Gate | Required | Actual | Status |",
            "|---|---:|---:|---|",
        ]
    )
    for name, gate in comparison["gates"].items():
        required = gate.get("minimum", gate.get("required"))
        lines.append(
            f"| {name} | {required} | {gate['actual']} | {'PASS' if gate['passed'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "> Passing this comparison permits continued research and optional integration;",
            "> it is not architectural, regulatory, accessibility, or structural certification.",
            "",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare the CP-SAT candidate to the baseline.")
    parser.add_argument("--dataset", type=Path, default=Path("data/benchmarks/v1"))
    parser.add_argument("--json", type=Path, help="Optional JSON comparison destination.")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown comparison destination.")
    parser.add_argument("--enforce", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    _manifest, cases = load_benchmark(args.dataset)
    baseline = evaluate_benchmark(
        cases,
        generator=get_candidate(DETERMINISTIC_BASELINE_NAME),
        candidate_name=DETERMINISTIC_BASELINE_NAME,
    )
    candidate = evaluate_benchmark(
        cases,
        generator=get_candidate(SOLVER_CANDIDATE_NAME),
        candidate_name=SOLVER_CANDIDATE_NAME,
    )
    comparison = compare_reports(baseline, candidate)
    markdown = comparison_to_markdown(comparison)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            f"{json.dumps(comparison, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 1 if args.enforce and not comparison["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
