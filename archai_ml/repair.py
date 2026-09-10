"""Deterministic projection onto the supported corridor/perimeter slot family.

The network proposes boxes; CP-SAT chooses a bijection from requested rooms to
fixed feasible slots. This is a restricted projection, not a free-form floor-plan
solver. No proposal or unvalidated fallback is returned on solver failure.
"""

import math
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from archai.datasets.pilot import layout_record
from archai.datasets.schema import canonicalize, geometry_key
from archai.models import DesignBrief, Layout
from archai.services.compliance import analyze_compliance
from archai.services.layout_generator import (
    ROOM_LIBRARY,
    _room_specs,
    building_bounds_for_brief,
    generate_layouts,
    layout_from_assignments,
)
from archai.services.solver_generator import (
    SOLVER_VARIATIONS,
    _cp_model_module,
    _preferred_pair_weights,
    _same_side_neighbor,
)
from archai.services.topology import HABITABLE_ROOM_TYPES, build_topology
from archai.services.zoning import build_zones

REPAIR_VERSION = "corridor-slot-projection-v1"


@dataclass(frozen=True)
class RepairConfig:
    deterministic_limit: float = 0.03
    adjacency_reward: int = 500
    passes: int = 2
    minimum_separation: float = 0.025

    def validate(self):
        if (type(self.deterministic_limit) not in (int, float)
                or not math.isfinite(self.deterministic_limit)
                or not 0 < self.deterministic_limit <= 10):
            raise ValueError("Invalid deterministic repair work limit.")
        if type(self.adjacency_reward) is not int or not 0 <= self.adjacency_reward <= 10000:
            raise ValueError("Invalid adjacency reward.")
        if type(self.passes) is not int or not 1 <= self.passes <= 4:
            raise ValueError("Repair passes must be between one and four.")
        if (type(self.minimum_separation) not in (int, float)
                or not math.isfinite(self.minimum_separation)
                or not 0 <= self.minimum_separation <= 1):
            raise ValueError("Invalid concept separation.")


DEFAULT_REPAIR_CONFIG = RepairConfig()


def program_specs(brief):
    return sorted(_room_specs(brief), key=lambda s: (s.type, s.label))


def validate_proposal(brief, proposal):
    specs = program_specs(brief)
    if (not isinstance(proposal, dict) or set(proposal) != {"room_types", "boxes"}
            or proposal["room_types"] != [s.type for s in specs]):
        raise ValueError("Proposal must match the canonical requested room program.")
    boxes = proposal["boxes"]
    if not isinstance(boxes, list) or len(boxes) != len(specs):
        raise ValueError("Proposal box count does not match the room program.")
    for box in boxes:
        if (not isinstance(box, list) or len(box) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 2
                       for v in box)
                or min(box[2:]) <= 0):
            raise ValueError("Proposal boxes must be finite normalized rectangles with positive sizes.")
    return specs


def validate_repaired(layout: Layout, brief: DesignBrief) -> dict:
    """Independent, stricter geometry checks followed by freshly derived topology."""
    expected = Counter(s.type for s in _room_specs(brief))
    if Counter(r.type for r in layout.rooms) != expected:
        raise ValueError("Repaired room program mismatch.")
    if len({r.id for r in layout.rooms}) != len(layout.rooms):
        raise ValueError("Duplicate repaired room IDs.")
    bounds = building_bounds_for_brief(brief)
    if layout.building_bounds != bounds:
        raise ValueError("Repaired footprint mismatch.")
    right, bottom = bounds["x"] + bounds["width"], bounds["y"] + bounds["depth"]
    for i, room in enumerate(layout.rooms):
        values = (room.x, room.y, room.width, room.depth)
        if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
            raise ValueError("Non-finite repaired geometry.")
        if min(room.width, room.depth) < 1.8 - 1e-9:
            raise ValueError("Repaired room below minimum dimension.")
        if room.area + 1e-6 < ROOM_LIBRARY[room.type]["minimum"]:
            raise ValueError("Repaired room below minimum area.")
        if (room.x < bounds["x"] - 1e-6 or room.y < bounds["y"] - 1e-6
                or room.x + room.width > right + 1e-6 or room.y + room.depth > bottom + 1e-6):
            raise ValueError("Repaired room outside footprint.")
        for other in layout.rooms[:i]:
            dx = max(0, min(room.x + room.width, other.x + other.width) - max(room.x, other.x))
            dy = max(0, min(room.y + room.depth, other.y + other.depth) - max(room.y, other.y))
            if dx * dy > 1e-6:
                raise ValueError("Repaired rooms overlap.")
    if abs(sum(r.area for r in layout.rooms) - bounds["width"] * bounds["depth"]) > 1e-4:
        raise ValueError("Repaired rooms do not cover the footprint.")
    layout.topology = build_topology(layout, accessibility=brief.accessibility)
    layout.zones = build_zones(layout, accessibility=brief.accessibility)
    openings = layout.topology["openings"]
    entries = [o for o in openings if o["kind"] == "entry_door"]
    if not entries:
        raise ValueError("Repaired plan has no entry door.")
    reached = set(entries[0]["room_ids"])
    while True:
        expanded = reached | {rid for o in openings if o["kind"] == "door"
                              and reached.intersection(o["room_ids"]) for rid in o["room_ids"]}
        if expanded == reached:
            break
        reached = expanded
    if reached != {r.id for r in layout.rooms}:
        raise ValueError("Repaired door graph is disconnected.")
    windows = {rid for o in openings if o["kind"] == "window" for rid in o["room_ids"]}
    if any(r.id not in windows for r in layout.rooms if r.type in HABITABLE_ROOM_TYPES):
        raise ValueError("Repaired habitable room lacks an exterior window.")
    compliance = analyze_compliance(layout, brief)
    if compliance["summary"]["errors"]:
        raise ValueError("Repaired topology or compliance checks failed.")
    return {"program": True, "boundary": True, "minimum_dimensions": True,
            "minimum_areas": True, "no_overlap": True, "coverage": True,
            "door_connectivity": True, "entry": True, "exterior_windows": True}


def _canonical(layout):
    return canonicalize(layout_record(layout, "projection", "projection", "archai-repair"))


def _slots(template, bounds):
    """Snap common endpoints once onto millimetres, preserving shared boundaries."""
    canonical = _canonical(template)
    w, h = bounds["width"], bounds["depth"]
    mappings = []
    for axis, limit in ((0, w), (1, h)):
        values = sorted({0.0, 1.0} | {v for room in canonical["rooms"] for v in
                        (room["box"][axis], room["box"][axis] + room["box"][axis + 2])})
        clusters = []
        # Canonical starts and sizes are independently rounded to eight decimals.
        # Merge only that representation error before choosing a shared mm edge.
        for value in values:
            if not clusters or value - clusters[-1][0] > 2e-8 + 1e-12:
                clusters.append([value])
            else:
                clusters[-1].append(value)
        mapping = {}
        for cluster in clusters:
            anchor = (0.0 if 0.0 in cluster else 1.0 if 1.0 in cluster
                      else sum(cluster) / len(cluster))
            edge = round(anchor * limit * 1000)
            mapping.update({value: edge for value in cluster})
        mappings.append(mapping)
    slots = []
    for room in canonical["rooms"]:
        x, y, rw, rh = room["box"]
        left, top = mappings[0][x], mappings[1][y]
        right, bottom = mappings[0][x + rw], mappings[1][y + rh]
        slots.append({"type": room["type"],
                      "box": [left / 1000, top / 1000, (right - left) / 1000, (bottom - top) / 1000]})
    return slots


def project_layout(brief, proposal, template, variant=0, config=DEFAULT_REPAIR_CONFIG):
    config.validate()
    specs = validate_proposal(brief, proposal)
    bounds = building_bounds_for_brief(brief)
    if template.building_bounds != bounds:
        raise ValueError("Template footprint mismatch.")
    slots = _slots(template, bounds)
    if Counter(s["type"] for s in slots) != Counter(s.type for s in specs):
        raise ValueError("Template room program mismatch.")
    cp = _cp_model_module()
    model, count = cp.CpModel(), len(specs)
    choices = [[model.new_bool_var(f"room-{i}-slot-{j}") for j in range(count)]
               for i in range(count)]
    corridor_slot = next(i for i, s in enumerate(slots) if s["type"] == "corridor")
    horizontal = bounds["width"] <= bounds["depth"]
    sides, ranks = {}, {}
    for side in (0, 1):
        ordered = sorted((j for j, s in enumerate(slots) if j != corridor_slot
                          and int(s["box"][1 if horizontal else 0]
                                  > slots[corridor_slot]["box"][1 if horizontal else 0]) == side),
                         key=lambda j: slots[j]["box"][0 if horizontal else 1])
        for rank, j in enumerate(ordered):
            sides[j], ranks[j] = side, rank
    sides[corridor_slot], ranks[corridor_slot] = 0, 0
    side_vars, positions, displacement = [], [], []
    hint_slots = {}
    for j, slot in enumerate(slots):
        hint_slots.setdefault(slot["type"], []).append(j)
    for i, spec in enumerate(specs):
        model.add_exactly_one(choices[i])
        hint = hint_slots[spec.type].pop(0)
        for j, slot in enumerate(slots):
            x, y, w, h = slot["box"]
            if ((spec.type == "corridor") != (j == corridor_slot)
                    or min(w, h) < 1.8 or w * h + 1e-6 < spec.minimum_area):
                model.add(choices[i][j] == 0)
            normalized = [x / bounds["width"], y / bounds["depth"],
                          w / bounds["width"], h / bounds["depth"]]
            cost = round(1000 * sum(abs(a - b) for a, b in
                                    zip(normalized, proposal["boxes"][i], strict=True)))
            displacement.append(cost * choices[i][j])
            model.add_hint(choices[i][j], int(j == hint))
        side = model.new_bool_var(f"side-{i}")
        pos = model.new_int_var(0, count, f"position-{i}")
        model.add(side == sum(sides[j] * choices[i][j] for j in range(count)))
        model.add(pos == sum(ranks[j] * choices[i][j] for j in range(count)))
        model.add_hint(side, sides[hint])
        model.add_hint(pos, ranks[hint])
        side_vars.append(side)
        positions.append(pos)
    for j in range(count):
        model.add_exactly_one(choices[i][j] for i in range(count))
    _, _, seed, multipliers = SOLVER_VARIATIONS[variant % len(SOLVER_VARIATIONS)]
    rewards = []
    for i, j, weight in _preferred_pair_weights(specs, multipliers):
        if "corridor" not in (specs[i].type, specs[j].type):
            adjacent = _same_side_neighbor(model, side_vars[i], side_vars[j],
                                           positions[i], positions[j], f"{i}-{j}")
            rewards.append(weight * adjacent)
    model.minimize(sum(displacement) - config.adjacency_reward * sum(rewards))
    solver = cp.CpSolver()
    solver.parameters.max_deterministic_time = config.deterministic_limit
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    if status not in (cp.OPTIMAL, cp.FEASIBLE):
        raise ValueError(f"No repair solution: {solver.status_name(status)}.")
    assignments, movement = [], []
    for i, spec in enumerate(specs):
        j = next(j for j in range(count) if solver.value(choices[i][j]))
        x, y, w, h = slots[j]["box"]
        assignments.append((spec, (bounds["x"] + x, bounds["y"] + y, w, h)))
        normalized = [x / bounds["width"], y / bounds["depth"],
                      w / bounds["width"], h / bounds["depth"]]
        movement.extend(abs(a - b) for a, b in zip(normalized, proposal["boxes"][i], strict=True))
    layout = layout_from_assignments(brief, variant, f"Repaired concept {variant + 1}",
                                     "Slot projection with functional adjacency", bounds, assignments)
    gates = validate_repaired(layout, brief)
    layout.id = f"archai-repaired-{variant + 1}"
    layout.metrics["repair"] = {"version": REPAIR_VERSION, "status": solver.status_name(status),
                                "objective": solver.objective_value, "bound": solver.best_objective_bound,
                                "coordinate_mae_displacement": sum(movement) / len(movement),
                                "max_coordinate_displacement": max(movement), "gates": gates}
    return layout


def _minimum_matching_cost(first, second):
    @lru_cache(None)
    def match(i, used):
        if i == len(first):
            return 0.0
        return min(math.dist(first[i], second[j]) + match(i + 1, used | (1 << j))
                   for j in range(len(second)) if not used & (1 << j))

    return match(0, 0)


def concept_distance(first, second):
    """Mean center distance / footprint diagonal; match repeated room types optimally."""
    bounds = first.building_bounds
    w, h = bounds["width"], bounds["depth"]
    groups = {}
    for layout, key in ((first, "a"), (second, "b")):
        for r in layout.rooms:
            groups.setdefault(r.type, {"a": [], "b": []})[key].append(
                (r.x + r.width / 2 - bounds["x"], r.y + r.depth / 2 - bounds["y"]))
    if any(len(g["a"]) != len(g["b"]) for g in groups.values()):
        raise ValueError("Diversity comparison requires identical room programs.")
    totals = []
    # Reflections of the whole plan do not create additional design concepts.
    for flip_x, flip_y in ((False, False), (True, False), (False, True), (True, True)):
        total = 0.0
        for group in groups.values():
            a = group["a"]
            b = [(w - x if flip_x else x, h - y if flip_y else y) for x, y in group["b"]]

            total += _minimum_matching_cost(a, b)
        totals.append(total / (len(first.rooms) * math.hypot(w, h)))
    return min(totals)


def repair_candidates(brief, proposal, config=DEFAULT_REPAIR_CONFIG):
    from archai.evaluation.benchmark import adjacency_satisfaction_score

    config.validate()
    validate_proposal(brief, proposal)
    templates = sorted(generate_layouts(brief), key=lambda layout: layout.id)
    pool, failures = [], []
    for repeat in range(config.passes):
        for index, template in enumerate(templates):
            try:
                pool.append(project_layout(brief, proposal, template,
                                           (index + repeat) % 5, config))
            except ValueError as exc:
                failures.append(str(exc))
    pool.sort(key=lambda layout: (-adjacency_satisfaction_score(layout, brief),
                                  layout.metrics["repair"]["coordinate_mae_displacement"],
                                  geometry_key(_canonical(layout), 3)))
    selected, seen = [], set()
    for layout in pool:
        key = geometry_key(_canonical(layout), 3)
        if key in seen or any(concept_distance(layout, other) < config.minimum_separation
                              for other in selected):
            continue
        seen.add(key)
        layout.id = f"archai-repaired-{len(selected) + 1}"
        layout.name = f"Repaired concept {len(selected) + 1}"
        selected.append(layout)
        if len(selected) == 5:
            break
    diagnostics = {"attempts": len(templates) * config.passes, "feasible": len(pool),
                   "returned": len(selected), "failures": failures,
                   "diversity_shortfall": len(selected) < 5}
    if not selected:
        raise ValueError(f"No validated repair available: {failures}")
    return selected, diagnostics
