"""Transparent preliminary residential design checks.

These checks are design-assistance heuristics, not a permit or professional
certification. Jurisdiction-specific rule packs are a later milestone.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from archai.models import DesignBrief, Layout, Room
from archai.services.layout_generator import ROOM_LIBRARY, adjacency_pairs


def _issue(rule: str, severity: str, message: str, suggestion: str) -> dict[str, str]:
    return {"rule": rule, "severity": severity, "message": message, "suggestion": suggestion}


def _overlap_area(a: Room, b: Room) -> float:
    width = max(0.0, min(a.x + a.width, b.x + b.width) - max(a.x, b.x))
    depth = max(0.0, min(a.y + a.depth, b.y + b.depth) - max(a.y, b.y))
    return width * depth


def analyze_compliance(layout: Layout, brief: DesignBrief | None = None) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    bounds = layout.building_bounds
    right = bounds["x"] + bounds["width"]
    bottom = bounds["y"] + bounds["depth"]

    for room in layout.rooms:
        minimum = ROOM_LIBRARY.get(room.type, {}).get("minimum", 4.0)
        if room.area + 0.01 < float(minimum):
            issues.append(
                _issue(
                    "ROOM_MIN_AREA",
                    "error",
                    f"{room.label} is {room.area:.1f} m²; the MVP rule minimum is {minimum:.1f} m².",
                    "Increase the room area or reduce competing space requirements.",
                )
            )
        if room.width < 1.8 or room.depth < 1.8:
            issues.append(
                _issue(
                    "ROOM_MIN_DIMENSION",
                    "warning",
                    f"{room.label} has a narrow dimension below 1.8 m.",
                    "Resize the room to improve usable clearance.",
                )
            )
        if (
            room.x < bounds["x"] - 0.01
            or room.y < bounds["y"] - 0.01
            or room.x + room.width > right + 0.01
            or room.y + room.depth > bottom + 0.01
        ):
            issues.append(
                _issue(
                    "BUILDING_BOUNDARY",
                    "error",
                    f"{room.label} extends beyond the proposed building footprint.",
                    "Move or resize the room so it remains inside the footprint.",
                )
            )

    for index, room_a in enumerate(layout.rooms):
        for room_b in layout.rooms[index + 1 :]:
            if _overlap_area(room_a, room_b) > 0.05:
                issues.append(
                    _issue(
                        "ROOM_OVERLAP",
                        "error",
                        f"{room_a.label} overlaps {room_b.label}.",
                        "Separate the two rooms before exporting the concept.",
                    )
                )

    pairs = adjacency_pairs(layout.rooms)
    graph: dict[str, set[str]] = defaultdict(set)
    type_pairs: set[frozenset[str]] = set()
    for room_a, room_b, _length in pairs:
        graph[room_a.id].add(room_b.id)
        graph[room_b.id].add(room_a.id)
        type_pairs.add(frozenset((room_a.type, room_b.type)))

    if frozenset(("kitchen", "dining")) not in type_pairs:
        issues.append(
            _issue(
                "FUNCTIONAL_ADJACENCY",
                "warning",
                "The kitchen does not share a boundary with the dining room.",
                "Move the kitchen and dining room closer for a more efficient service path.",
            )
        )

    if layout.rooms and not layout.topology:
        visited: set[str] = set()
        queue = deque([layout.rooms[0].id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend(graph[current] - visited)
        if len(visited) != len(layout.rooms):
            issues.append(
                _issue(
                    "CIRCULATION_GRAPH",
                    "error",
                    "One or more rooms are disconnected from the layout adjacency graph.",
                    "Add a shared boundary or circulation zone connecting every room.",
                )
            )

    if layout.topology:
        for topology_issue in layout.topology.get("issues", []):
            issues.append(
                _issue(
                    str(topology_issue["code"]),
                    str(topology_issue["severity"]),
                    str(topology_issue["message"]),
                    str(topology_issue["suggestion"]),
                )
            )
        for zoning_issue in layout.zones.get("issues", []):
            issues.append(
                _issue(
                    str(zoning_issue["code"]),
                    str(zoning_issue["severity"]),
                    str(zoning_issue["message"]),
                    str(zoning_issue["suggestion"]),
                )
            )
    else:
        for room in layout.rooms:
            if room.type not in {"bedroom", "living", "study"}:
                continue
            exterior = (
                abs(room.x - bounds["x"]) < 0.05
                or abs(room.y - bounds["y"]) < 0.05
                or abs(room.x + room.width - right) < 0.05
                or abs(room.y + room.depth - bottom) < 0.05
            )
            if not exterior:
                issues.append(
                    _issue(
                        "DAYLIGHT_POTENTIAL",
                        "warning",
                        f"{room.label} has no exterior wall for a conventional window.",
                        "Move the room to the perimeter or design a verified light-well solution.",
                    )
                )

    if layout.floor_area >= 200:
        issues.append(
            _issue(
                "EGRESS_REVIEW",
                "warning",
                "The concept exceeds 200 m² and needs a jurisdiction-specific egress review.",
                "Have a qualified professional verify exit count, travel distance, and fire separation.",
            )
        )

    if brief and brief.accessibility:
        narrow_doors = [
            opening
            for opening in layout.topology.get("openings", [])
            if opening.get("kind") in {"door", "entry_door"}
            and float(opening.get("width_m", 0)) < 1.0
        ]
        if narrow_doors:
            issues.append(
                _issue(
                    "ACCESSIBLE_DOOR_WIDTH",
                    "warning",
                    f"{len(narrow_doors)} concept door(s) are narrower than the 1.0 m project target.",
                    "Widen the affected wall segments and rebuild the door topology.",
                )
            )
        else:
            turning_circles = int(layout.zones.get("summary", {}).get("turning_circles", 0))
            issues.append(
                _issue(
                    "ACCESSIBILITY_DETAIL",
                    "info",
                    f"Concept doors use the 1.0 m target and include {turning_circles} turning circle(s).",
                    "A qualified professional must still verify clear openings, approaches, and turning spaces.",
                )
            )

    error_count = sum(issue["severity"] == "error" for issue in issues)
    warning_count = sum(issue["severity"] == "warning" for issue in issues)
    score = max(0, 100 - error_count * 15 - warning_count * 6)
    status = "fail" if error_count else "review" if warning_count else "pass"
    return {
        "status": status,
        "score": score,
        "summary": {
            "errors": error_count,
            "warnings": warning_count,
            "info": len(issues) - error_count - warning_count,
        },
        "issues": issues,
        "disclaimer": "Preliminary concept checks only. This is not a building permit, code certification, structural analysis, or professional advice.",
    }
