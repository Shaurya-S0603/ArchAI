"""Bounded, strictly validated room-proportion diversity within the corridor family."""

import math

from archai.datasets.schema import geometry_key
from archai.evaluation.benchmark import adjacency_satisfaction_score
from archai.services.layout_generator import layout_from_assignments
from archai_ml.repair import (
    DEFAULT_REPAIR_CONFIG,
    _canonical,
    concept_distance,
    repair_candidates,
    validate_proposal,
    validate_repaired,
)

DIVERSITY_VERSION = "adaptive-corridor-diversity-v1"
REFLOW_FRACTIONS = (.5, .25, .75, .125, .875, 0., 1., .375, .625)
MAXIMUM_SEARCH_NODES = 20000


def reflow_variants(brief, proposal, parent):
    """Move shared corridor edges once; never round neighboring rooms separately."""
    specs = validate_proposal(brief, proposal)
    validate_repaired(parent, brief)
    rooms = sorted(parent.rooms, key=lambda r: (r.type, r.label))
    bounds = parent.building_bounds
    horizontal = bounds["width"] <= bounds["depth"]
    axis = 1 if horizontal else 0
    extent = round(bounds["depth" if horizontal else "width"] * 1000)
    boxes = [[round((r.x - bounds["x"]) * 1000), round((r.y - bounds["y"]) * 1000),
              round(r.width * 1000), round(r.depth * 1000)] for r in rooms]
    corridor = next(i for i, r in enumerate(rooms) if r.type == "corridor")
    old_start, thickness = boxes[corridor][axis], boxes[corridor][axis + 2]
    required = [1800, 1800]
    for i, spec in enumerate(specs):
        if i == corridor:
            continue
        side = int(boxes[i][axis] > old_start)
        span = boxes[i][3 - axis]
        required[side] = max(required[side], math.ceil(spec.minimum_area * 1e6 / span))
    low, high = required[0], extent - thickness - required[1]
    if high < low:
        return
    for fraction in REFLOW_FRACTIONS:
        start = low + round((high - low) * fraction)
        assignments, movement = [], []
        for i, (spec, source) in enumerate(zip(specs, boxes, strict=True)):
            box = source.copy()
            if i == corridor:
                box[axis] = start
            elif source[axis] < old_start:
                box[axis], box[axis + 2] = 0, start
            else:
                box[axis], box[axis + 2] = start + thickness, extent - start - thickness
            x, y, w, h = [v / 1000 for v in box]
            assignments.append((spec, (bounds["x"] + x, bounds["y"] + y, w, h)))
            normalized = [x / bounds["width"], y / bounds["depth"],
                          w / bounds["width"], h / bounds["depth"]]
            movement.extend(abs(a - b) for a, b in zip(normalized, proposal["boxes"][i], strict=True))
        layout = layout_from_assignments(brief, 0, "Diverse concept", "Corridor proportion variation",
                                         bounds, assignments)
        gates = validate_repaired(layout, brief)
        layout.metrics["repair"] = {
            "version": DIVERSITY_VERSION, "status": "VALIDATED_REFLOW",
            "source_status": parent.metrics["repair"]["status"],
            "coordinate_mae_displacement": sum(movement) / len(movement),
            "max_coordinate_displacement": max(movement), "gates": gates,
        }
        yield layout


def select_distinct(pool, minimum_separation, maximum_nodes=MAXIMUM_SEARCH_NODES):
    """Bounded compatible-set search avoids a greedy anchor excluding a valid set."""
    distances, nodes, best = {}, 0, []

    def compatible(i, j):
        key = (min(i, j), max(i, j))
        if key not in distances:
            distances[key] = concept_distance(pool[i], pool[j]) >= minimum_separation
        return distances[key]

    def search(chosen, available):
        nonlocal nodes, best
        nodes += 1
        if len(chosen) > len(best):
            best = chosen
        if len(best) == 5 or nodes >= maximum_nodes:
            return True
        if len(chosen) + len(available) <= len(best):
            return False
        for offset, index in enumerate(available):
            remaining = [j for j in available[offset + 1:] if compatible(index, j)]
            if search(chosen + [index], remaining):
                return True
        return False

    search([], list(range(len(pool))))
    return [pool[i] for i in best], nodes


def diverse_candidates(brief, proposal, config=DEFAULT_REPAIR_CONFIG):
    parents, diagnostics = repair_candidates(brief, proposal, config)
    selected, pool, seen, nodes, expanded = parents, list(parents), set(), 0, 0
    for layout in pool:
        seen.add(geometry_key(_canonical(layout), 3))
    if len(selected) < 5:
        for parent in parents:
            for layout in reflow_variants(brief, proposal, parent):
                key = geometry_key(_canonical(layout), 3)
                if key not in seen:
                    pool.append(layout)
                    seen.add(key)
                    expanded += 1
            pool.sort(key=lambda l: (-adjacency_satisfaction_score(l, brief),
                                     l.metrics["repair"]["coordinate_mae_displacement"],
                                     geometry_key(_canonical(l), 3)))
            selected, count = select_distinct(pool, config.minimum_separation,
                                               MAXIMUM_SEARCH_NODES - nodes)
            nodes += count
            if len(selected) == 5 or nodes >= MAXIMUM_SEARCH_NODES:
                break
    for i, layout in enumerate(selected):
        layout.id, layout.name = f"archai-diverse-{i + 1}", f"Diverse concept {i + 1}"
    return selected, {**diagnostics, "returned": len(selected), "expanded": expanded,
                      "selection_nodes": nodes, "diversity_shortfall": len(selected) < 5}


def validate_concepts(layouts, brief, minimum_separation=.025):
    """Independent serving boundary, including cardinality and duplicate checks."""
    if not isinstance(layouts, list) or len(layouts) != 5:
        raise ValueError("Experimental generator must return five concepts.")
    seen = set()
    for i, layout in enumerate(layouts):
        validate_repaired(layout, brief)
        key = geometry_key(_canonical(layout), 3)
        if key in seen or any(concept_distance(layout, other) < minimum_separation
                              for other in layouts[:i]):
            raise ValueError("Experimental concepts are insufficiently distinct.")
        seen.add(key)
