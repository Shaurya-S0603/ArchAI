from collections import Counter

import pytest

from archai.evaluation.benchmark import adjacency_satisfaction_score, evaluate_benchmark
from archai.evaluation.comparison import compare_reports, comparison_to_markdown
from archai.evaluation.dataset import build_synthetic_cases
from archai.models import DesignBrief
from archai.services.layout_generator import generate_layouts
from archai.services.solver_generator import (
    SOLVER_CANDIDATE_NAME,
    SolverUnavailableError,
    generate_solver_layouts,
)


def test_solver_candidate_is_deterministic_and_preserves_program(brief):
    design_brief = DesignBrief.from_dict(brief)
    first = generate_solver_layouts(design_brief)
    second = generate_solver_layouts(design_brief)

    assert [layout.to_dict() for layout in first] == [layout.to_dict() for layout in second]
    assert len(first) == 5
    expected = Counter(
        {
            "corridor": 1,
            "living": 1,
            "kitchen": 1,
            "dining": 1,
            "bedroom": brief["bedrooms"],
            "bathroom": brief["bathrooms"],
            "study": 1,
        }
    )
    for layout in first:
        assert Counter(room.type for room in layout.rooms) == expected
        assert layout.topology["issues"] == []
        assert layout.metrics["solver"]["candidate"] == SOLVER_CANDIDATE_NAME


def test_solver_improves_functional_adjacency_on_reference_brief(brief):
    design_brief = DesignBrief.from_dict(brief)
    baseline = generate_layouts(design_brief)
    candidate = generate_solver_layouts(design_brief)
    baseline_score = sum(adjacency_satisfaction_score(layout, design_brief) for layout in baseline)
    candidate_score = sum(
        adjacency_satisfaction_score(layout, design_brief) for layout in candidate
    )

    assert candidate_score > baseline_score


def test_solver_dependency_error_is_actionable(monkeypatch, brief):
    from archai.services import solver_generator

    def missing_dependency(_name):
        raise ModuleNotFoundError

    monkeypatch.setattr(solver_generator, "import_module", missing_dependency)
    with pytest.raises(SolverUnavailableError, match="requirements-solver.txt"):
        generate_solver_layouts(DesignBrief.from_dict(brief))


def test_candidate_comparison_requires_improvement():
    cases = build_synthetic_cases(count=4)
    baseline = evaluate_benchmark(cases)
    candidate = evaluate_benchmark(
        cases,
        generator=generate_solver_layouts,
        candidate_name=SOLVER_CANDIDATE_NAME,
    )
    comparison = compare_reports(baseline, candidate)

    assert comparison["passed"] is True
    assert comparison["deltas"]["mean_adjacency_satisfaction"] >= 0.05
    assert "Promotion gate: **PASS**" in comparison_to_markdown(comparison)
