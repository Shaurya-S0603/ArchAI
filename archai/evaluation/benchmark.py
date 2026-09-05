"""Generator-independent metrics and regression gates for ArchAI."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import combinations
from math import hypot
from statistics import fmean
from typing import Any

from archai.evaluation.dataset import BenchmarkCase, dataset_digest
from archai.models import DesignBrief, Layout
from archai.services.compliance import analyze_compliance
from archai.services.cost_estimator import estimate_cost
from archai.services.layout_generator import (
    PREFERRED_ADJACENCIES,
    adjacency_pairs,
    generate_layouts,
)
from archai.version import VERSION

Generator = Callable[[DesignBrief], list[Layout]]

DEFAULT_THRESHOLDS = {
    "case_success_rate": 1.0,
    "concept_count_pass_rate": 1.0,
    "hard_constraint_pass_rate": 1.0,
    "program_match_rate": 1.0,
    "mean_adjacency_satisfaction": 0.60,
    "mean_diversity_score": 0.08,
}


def _mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0


def _expected_program(brief: DesignBrief) -> Counter[str]:
    program = Counter({"corridor": 1, "living": 1, "kitchen": 1, "dining": 1})
    program["bedroom"] += brief.bedrooms
    program["bathroom"] += brief.bathrooms
    program.update(brief.other_rooms)
    return program


def program_match_score(layout: Layout, brief: DesignBrief) -> float:
    expected = _expected_program(brief)
    actual = Counter(room.type for room in layout.rooms)
    total = sum(expected.values())
    matched = sum(min(expected[room_type], actual[room_type]) for room_type in expected)
    unexpected = sum((actual - expected).values())
    return max(0.0, (matched - unexpected) / max(total, 1))


def adjacency_satisfaction_score(layout: Layout, brief: DesignBrief) -> float:
    """Score requested functional relationships without rewarding duplicates."""

    expected = _expected_program(brief)
    required_counts: dict[frozenset[str], int] = {}
    for relationship in PREFERRED_ADJACENCIES:
        first, second = tuple(relationship)
        if first == second:
            possible = expected[first] // 2
        else:
            possible = min(expected[first], expected[second])
        if possible:
            required_counts[relationship] = possible

    achieved_counts: Counter[frozenset[str]] = Counter(
        frozenset((first.type, second.type))
        for first, second, _length in adjacency_pairs(layout.rooms)
    )
    possible_weight = sum(
        PREFERRED_ADJACENCIES[relationship] * count
        for relationship, count in required_counts.items()
    )
    achieved_weight = sum(
        PREFERRED_ADJACENCIES[relationship] * min(count, achieved_counts[relationship])
        for relationship, count in required_counts.items()
    )
    return achieved_weight / max(possible_weight, 1)


def _room_centers(layout: Layout) -> dict[tuple[str, int], tuple[float, float]]:
    counts: Counter[str] = Counter()
    centers: dict[tuple[str, int], tuple[float, float]] = {}
    for room in sorted(layout.rooms, key=lambda item: (item.type, item.label)):
        counts[room.type] += 1
        centers[(room.type, counts[room.type])] = (
            room.x + room.width / 2,
            room.y + room.depth / 2,
        )
    return centers


def layout_diversity_score(layouts: list[Layout]) -> float:
    """Mean normalized room-center displacement across every concept pair."""

    if len(layouts) < 2:
        return 0.0
    pair_scores: list[float] = []
    for first, second in combinations(layouts, 2):
        first_centers = _room_centers(first)
        second_centers = _room_centers(second)
        shared = sorted(first_centers.keys() & second_centers.keys())
        diagonal = hypot(first.site_width_m, first.site_depth_m)
        distances = [
            hypot(
                first_centers[key][0] - second_centers[key][0],
                first_centers[key][1] - second_centers[key][1],
            )
            / max(diagonal, 0.01)
            for key in shared
        ]
        pair_scores.append(min(1.0, _mean(distances)))
    return _mean(pair_scores)


def _accessibility_score(layout: Layout, brief: DesignBrief) -> float:
    if not brief.accessibility:
        return 1.0
    doors = [
        opening
        for opening in layout.topology.get("openings", [])
        if opening.get("kind") in {"door", "entry_door"}
    ]
    door_score = sum(float(door.get("width_m", 0)) >= 1.0 for door in doors) / max(len(doors), 1)
    expected_turning = brief.bathrooms + 1
    actual_turning = int(layout.zones.get("summary", {}).get("turning_circles", 0))
    turning_score = min(1.0, actual_turning / max(expected_turning, 1))
    return (door_score + turning_score) / 2


def _evaluate_case(case: BenchmarkCase, generator: Generator) -> dict[str, Any]:
    try:
        layouts = generator(case.brief)
    except (ValueError, RuntimeError) as exc:
        return {
            "case_id": case.id,
            "split": case.split,
            "generation_success": False,
            "error": str(exc),
            "concept_count": 0,
            "concept_count_pass": False,
            "hard_constraint_pass_rate": 0.0,
            "program_match_rate": 0.0,
            "mean_adjacency_satisfaction": 0.0,
            "diversity_score": 0.0,
            "budget_fit_rate": 0.0,
            "accessibility_score": 0.0,
            "user_alignment_score": 0.0,
        }

    compliance = [analyze_compliance(layout, case.brief) for layout in layouts]
    costs = [estimate_cost(layout, case.brief) for layout in layouts]
    hard_constraint_pass = [result["summary"]["errors"] == 0 for result in compliance]
    program_scores = [program_match_score(layout, case.brief) for layout in layouts]
    adjacency_scores = [adjacency_satisfaction_score(layout, case.brief) for layout in layouts]
    budget_scores = [result["within_budget"] is not False for result in costs]
    accessibility_scores = [_accessibility_score(layout, case.brief) for layout in layouts]
    style_scores = [layout.style == case.brief.style for layout in layouts]

    hard_constraint_rate = _mean([float(value) for value in hard_constraint_pass])
    program_rate = _mean(program_scores)
    budget_rate = _mean([float(value) for value in budget_scores])
    accessibility_rate = _mean(accessibility_scores)
    style_rate = _mean([float(value) for value in style_scores])
    alignment = (
        0.35 * program_rate
        + 0.25 * hard_constraint_rate
        + 0.15 * style_rate
        + 0.15 * accessibility_rate
        + 0.10 * budget_rate
    )

    return {
        "case_id": case.id,
        "split": case.split,
        "generation_success": True,
        "error": None,
        "concept_count": len(layouts),
        "concept_count_pass": len(layouts) == 5,
        "hard_constraint_pass_rate": round(hard_constraint_rate, 4),
        "program_match_rate": round(program_rate, 4),
        "mean_adjacency_satisfaction": round(_mean(adjacency_scores), 4),
        "diversity_score": round(layout_diversity_score(layouts), 4),
        "budget_fit_rate": round(budget_rate, 4),
        "accessibility_score": round(accessibility_rate, 4),
        "user_alignment_score": round(alignment, 4),
    }


def evaluate_benchmark(
    cases: list[BenchmarkCase],
    generator: Generator = generate_layouts,
    candidate_name: str = "deterministic-baseline",
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    if not cases:
        raise ValueError("At least one benchmark case is required.")

    applied_thresholds = dict(DEFAULT_THRESHOLDS if thresholds is None else thresholds)
    case_results = [_evaluate_case(case, generator) for case in cases]
    summary = {
        "case_count": len(cases),
        "case_success_rate": round(
            _mean([float(result["generation_success"]) for result in case_results]), 4
        ),
        "concept_count_pass_rate": round(
            _mean([float(result["concept_count_pass"]) for result in case_results]), 4
        ),
        "hard_constraint_pass_rate": round(
            _mean([result["hard_constraint_pass_rate"] for result in case_results]), 4
        ),
        "program_match_rate": round(
            _mean([result["program_match_rate"] for result in case_results]), 4
        ),
        "mean_adjacency_satisfaction": round(
            _mean([result["mean_adjacency_satisfaction"] for result in case_results]), 4
        ),
        "mean_diversity_score": round(
            _mean([result["diversity_score"] for result in case_results]), 4
        ),
        "budget_fit_rate": round(_mean([result["budget_fit_rate"] for result in case_results]), 4),
        "mean_accessibility_score": round(
            _mean([result["accessibility_score"] for result in case_results]), 4
        ),
        "mean_user_alignment_score": round(
            _mean([result["user_alignment_score"] for result in case_results]), 4
        ),
    }
    gates = {
        metric: {
            "minimum": minimum,
            "actual": summary[metric],
            "passed": summary[metric] >= minimum,
        }
        for metric, minimum in applied_thresholds.items()
    }
    return {
        "report_schema_version": 1,
        "application_version": VERSION,
        "candidate": candidate_name,
        "evaluated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dataset_sha256": dataset_digest(cases),
        "summary": summary,
        "thresholds": applied_thresholds,
        "gates": gates,
        "passed": all(gate["passed"] for gate in gates.values()),
        "cases": case_results,
    }


def report_to_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    rows = [
        ("Cases evaluated", str(summary["case_count"])),
        ("Generation success", f"{summary['case_success_rate']:.1%}"),
        ("Five-concept contract", f"{summary['concept_count_pass_rate']:.1%}"),
        ("Hard-constraint pass", f"{summary['hard_constraint_pass_rate']:.1%}"),
        ("Room-program match", f"{summary['program_match_rate']:.1%}"),
        ("Adjacency satisfaction", f"{summary['mean_adjacency_satisfaction']:.1%}"),
        ("Mean diversity score", f"{summary['mean_diversity_score']:.4f}"),
        ("Budget fit", f"{summary['budget_fit_rate']:.1%}"),
        ("Accessibility alignment", f"{summary['mean_accessibility_score']:.1%}"),
        ("User alignment", f"{summary['mean_user_alignment_score']:.1%}"),
    ]
    gate_rows = [
        (
            metric,
            str(gate["minimum"]),
            str(gate["actual"]),
            "PASS" if gate["passed"] else "FAIL",
        )
        for metric, gate in report["gates"].items()
    ]
    lines = [
        "# ArchAI Generator Benchmark",
        "",
        f"- Application: `{report['application_version']}`",
        f"- Candidate: `{report['candidate']}`",
        f"- Dataset SHA-256: `{report['dataset_sha256']}`",
        f"- Evaluated: `{report['evaluated_at']}`",
        f"- Overall gate: **{'PASS' if report['passed'] else 'FAIL'}**",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---:|",
        *[f"| {label} | {value} |" for label, value in rows],
        "",
        "## Regression gates",
        "",
        "| Metric | Minimum | Actual | Status |",
        "|---|---:|---:|---|",
        *[
            f"| {metric} | {minimum} | {actual} | {status} |"
            for metric, minimum, actual, status in gate_rows
        ],
        "",
        "> These metrics compare generator candidates; they are not building-code,",
        "> structural, accessibility, or professional design certification.",
        "",
    ]
    return "\n".join(lines)
