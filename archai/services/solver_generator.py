"""Optional CP-SAT candidate for Phase 2B layout ordering.

The solver optimizes which side of the circulation spine each room occupies and
the order of rooms along each side. Rectangle construction, topology, zoning,
and hard checks remain the same deterministic services used by the fallback.
"""

from __future__ import annotations

from importlib import import_module
from math import floor
from random import Random
from typing import Any

from archai.models import DesignBrief, Layout
from archai.services.layout_generator import (
    PREFERRED_ADJACENCIES,
    RoomSpec,
    _room_specs,
    _strip_partition,
    building_bounds_for_brief,
    layout_from_assignments,
)

SOLVER_CANDIDATE_NAME = "cp-sat-v1"
SOLVER_VARIATIONS = (
    ("Solver balanced", "CP-SAT balanced functional adjacency", 101, {}),
    (
        "Solver social core",
        "CP-SAT kitchen, dining, and living adjacency",
        211,
        {frozenset(("kitchen", "dining")): 3, frozenset(("living", "dining")): 3},
    ),
    (
        "Solver private suite",
        "CP-SAT bedroom and bathroom adjacency",
        307,
        {frozenset(("bedroom", "bathroom")): 4},
    ),
    (
        "Solver service core",
        "CP-SAT service-space adjacency",
        401,
        {frozenset(("garage", "utility")): 5, frozenset(("kitchen", "dining")): 2},
    ),
    ("Solver diverse", "CP-SAT alternate optimum", 503, {}),
)


class SolverUnavailableError(RuntimeError):
    """Raised when the optional solver dependency has not been installed."""


def _cp_model_module():
    try:
        return import_module("ortools.sat.python.cp_model")
    except ModuleNotFoundError as exc:
        raise SolverUnavailableError(
            "The CP-SAT candidate requires the optional solver dependencies. "
            "Install them with: python -m pip install -r requirements-solver.txt"
        ) from exc


def _same_side_neighbor(model, first_side, second_side, first_pos, second_pos, name: str):
    same_side = model.new_bool_var(f"same-side-{name}")
    model.add(first_side == second_side).only_enforce_if(same_side)
    model.add(first_side != second_side).only_enforce_if(same_side.negated())

    distance = model.new_int_var(0, 100, f"distance-{name}")
    model.add_abs_equality(distance, first_pos - second_pos)
    consecutive = model.new_bool_var(f"consecutive-{name}")
    model.add(distance == 1).only_enforce_if(consecutive)
    model.add(distance != 1).only_enforce_if(consecutive.negated())

    adjacent = model.new_bool_var(f"adjacent-{name}")
    model.add(adjacent <= same_side)
    model.add(adjacent <= consecutive)
    model.add(adjacent >= same_side + consecutive - 1)
    return adjacent


def _preferred_pair_weights(
    specs: list[RoomSpec], multipliers: dict[frozenset[str], int]
) -> list[tuple[int, int, int]]:
    pairs = []
    for first_index, first in enumerate(specs):
        for second_index, second in enumerate(specs[first_index + 1 :], start=first_index + 1):
            relationship = frozenset((first.type, second.type))
            base_weight = PREFERRED_ADJACENCIES.get(relationship, 0)
            if base_weight:
                pairs.append(
                    (
                        first_index,
                        second_index,
                        base_weight * multipliers.get(relationship, 1),
                    )
                )
    return pairs


def _solve_order(
    specs: list[RoomSpec],
    span_m: float,
    seed: int,
    multipliers: dict[frozenset[str], int],
) -> tuple[list[RoomSpec], list[RoomSpec], dict[str, Any]]:
    cp_model = _cp_model_module()
    room_count = len(specs)
    capacity = floor((span_m + 0.01) / 1.8)
    if room_count > capacity * 2:
        raise ValueError(
            "The site is too narrow for the CP-SAT candidate to retain 1.8 m room spans. "
            "Increase the site or reduce the room count."
        )

    model = cp_model.CpModel()
    side = [model.new_bool_var(f"side-{index}") for index in range(room_count)]
    position = [
        model.new_int_var(0, room_count - 1, f"position-{index}") for index in range(room_count)
    ]
    slot = [
        model.new_int_var(0, room_count * 2 - 1, f"slot-{index}") for index in range(room_count)
    ]
    for index in range(room_count):
        model.add(slot[index] == position[index] + room_count * side[index])
    model.add_all_different(slot)
    model.add(sum(side) >= 1)
    model.add(sum(side) <= room_count - 1)
    model.add(sum(side) <= capacity)
    model.add(room_count - sum(side) <= capacity)

    living_index = next((index for index, spec in enumerate(specs) if spec.type == "living"), 0)
    model.add(side[living_index] == 0)

    adjacency_terms = []
    for first, second, weight in _preferred_pair_weights(specs, multipliers):
        adjacent = _same_side_neighbor(
            model,
            side[first],
            side[second],
            position[first],
            position[second],
            f"{first}-{second}",
        )
        adjacency_terms.append(weight * adjacent)

    target_areas = [round(spec.target_area * 10) for spec in specs]
    total_area = sum(target_areas)
    second_side_area = sum(target_areas[index] * side[index] for index in range(room_count))
    imbalance = model.new_int_var(0, total_area, "side-area-imbalance")
    model.add_abs_equality(imbalance, total_area - 2 * second_side_area)

    rng = Random(seed)
    preferred_room_order = list(range(room_count))
    rng.shuffle(preferred_room_order)
    first_count = (room_count + 1) // 2
    preferred_slots: dict[int, int] = {}
    for rank, room_index in enumerate(preferred_room_order):
        if rank < first_count:
            preferred_slots[room_index] = rank
        else:
            preferred_slots[room_index] = room_count + rank - first_count
    deviations = []
    for index in range(room_count):
        deviation = model.new_int_var(0, room_count * 2, f"slot-deviation-{index}")
        model.add_abs_equality(deviation, slot[index] - preferred_slots[index])
        deviations.append(deviation)

    model.maximize(sum(adjacency_terms) * 1_000 - imbalance * 10 - sum(deviations))
    solver = cp_model.CpSolver()
    # Wall-clock cutoffs can stop at different solutions (or before any solution)
    # under CPU contention. A work budget preserves repeatability for this pinned
    # OR-Tools version and single-worker search; it is not a wall-time SLA.
    solver.parameters.max_deterministic_time = 0.1
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(f"The CP-SAT candidate could not solve this brief (status={status}).")

    first_indices = sorted(
        (index for index in range(room_count) if solver.value(side[index]) == 0),
        key=lambda index: solver.value(position[index]),
    )
    second_indices = sorted(
        (index for index in range(room_count) if solver.value(side[index]) == 1),
        key=lambda index: solver.value(position[index]),
    )
    first_side = [specs[index] for index in first_indices]
    second_side = [specs[index] for index in second_indices]
    diagnostics = {
        "candidate": SOLVER_CANDIDATE_NAME,
        "status": solver.status_name(status),
        "objective": round(solver.objective_value, 3),
        "best_bound": round(solver.best_objective_bound, 3),
        "deterministic_time_limit": 0.1,
    }
    return first_side, second_side, diagnostics


def _solver_partition(
    first: list[RoomSpec],
    second: list[RoomSpec],
    corridor: RoomSpec,
    bounds: dict[str, float],
) -> list[tuple[RoomSpec, tuple[float, float, float, float]]]:
    corridor_width = 1.8
    x, y = bounds["x"], bounds["y"]
    width, depth = bounds["width"], bounds["depth"]
    if width <= depth:
        side_depth = (depth - corridor_width) / 2
        corridor_rect = (x, y + side_depth, width, corridor_width)
        first_rect = (x, y, width, side_depth)
        second_rect = (x, y + side_depth + corridor_width, width, side_depth)
        return (
            [(corridor, corridor_rect)]
            + _strip_partition(first, first_rect, split_width=True)
            + _strip_partition(second, second_rect, split_width=True)
        )
    side_width = (width - corridor_width) / 2
    corridor_rect = (x + side_width, y, corridor_width, depth)
    first_rect = (x, y, side_width, depth)
    second_rect = (x + side_width + corridor_width, y, side_width, depth)
    return (
        [(corridor, corridor_rect)]
        + _strip_partition(first, first_rect, split_width=False)
        + _strip_partition(second, second_rect, split_width=False)
    )


def generate_solver_layouts(brief: DesignBrief) -> list[Layout]:
    """Generate five layouts with CP-SAT-optimized room ordering."""

    specs = _room_specs(brief)
    corridor = next(spec for spec in specs if spec.type == "corridor")
    spaces = [spec for spec in specs if spec.type != "corridor"]
    bounds = building_bounds_for_brief(brief)
    available_area = bounds["width"] * bounds["depth"]
    minimum_area = sum(spec.minimum_area for spec in specs)
    if minimum_area > available_area:
        raise ValueError(
            f"The requested rooms need at least {minimum_area:.0f} m², but the concept footprint "
            f"provides {available_area:.0f} m². Increase the site or remove rooms."
        )

    partition_span = min(bounds["width"], bounds["depth"])
    layouts: list[Layout] = []
    for index, (name, objective, seed, multipliers) in enumerate(SOLVER_VARIATIONS):
        first, second, diagnostics = _solve_order(spaces, partition_span, seed, multipliers)
        assignments = _solver_partition(first, second, corridor, bounds)
        layout = layout_from_assignments(brief, index, name, objective, bounds, assignments)
        layout.id = f"archai-solver-v{index + 1}"
        layout.metrics["solver"] = diagnostics
        layouts.append(layout)
    return sorted(layouts, key=lambda layout: layout.score, reverse=True)
