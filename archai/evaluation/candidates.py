"""Named generator candidates available to the evaluation harness."""

from __future__ import annotations

from archai.evaluation.benchmark import Generator
from archai.services.layout_generator import generate_layouts
from archai.services.solver_generator import SOLVER_CANDIDATE_NAME, generate_solver_layouts

DETERMINISTIC_BASELINE_NAME = "deterministic-baseline"
CANDIDATE_NAMES = (DETERMINISTIC_BASELINE_NAME, SOLVER_CANDIDATE_NAME)


def get_candidate(name: str) -> Generator:
    candidates = {
        DETERMINISTIC_BASELINE_NAME: generate_layouts,
        SOLVER_CANDIDATE_NAME: generate_solver_layouts,
    }
    try:
        return candidates[name]
    except KeyError as exc:
        raise ValueError(f"Unknown generator candidate: {name}.") from exc
