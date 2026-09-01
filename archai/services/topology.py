"""Derive semantic walls, openings, and circulation from rectangular rooms."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from archai.models import Layout, Room
from archai.services.layout_generator import PREFERRED_ADJACENCIES

COORDINATE_PRECISION = 3
GEOMETRY_TOLERANCE = 0.04
MINIMUM_DOOR_WIDTH_M = 0.8
HABITABLE_ROOM_TYPES = {"bedroom", "dining", "kitchen", "living", "lounge", "study"}


@dataclass(frozen=True)
class _RawEdge:
    orientation: str
    line: float
    start: float
    end: float
    room_id: str


def _coordinate(value: float) -> float:
    return round(value, COORDINATE_PRECISION)


def _room_edges(room: Room) -> tuple[_RawEdge, ...]:
    left = _coordinate(room.x)
    top = _coordinate(room.y)
    right = _coordinate(room.x + room.width)
    bottom = _coordinate(room.y + room.depth)
    return (
        _RawEdge("horizontal", top, left, right, room.id),
        _RawEdge("horizontal", bottom, left, right, room.id),
        _RawEdge("vertical", left, top, bottom, room.id),
        _RawEdge("vertical", right, top, bottom, room.id),
    )


def _is_exterior(orientation: str, line: float, bounds: dict[str, float]) -> bool:
    if orientation == "horizontal":
        edges = (bounds["y"], bounds["y"] + bounds["depth"])
    else:
        edges = (bounds["x"], bounds["x"] + bounds["width"])
    return any(abs(line - edge) <= GEOMETRY_TOLERANCE for edge in edges)


def _atomic_walls(layout: Layout) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, float], list[_RawEdge]] = defaultdict(list)
    for room in layout.rooms:
        for edge in _room_edges(room):
            grouped[(edge.orientation, edge.line)].append(edge)

    atomic: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for (orientation, line), edges in sorted(grouped.items()):
        breaks = sorted({edge.start for edge in edges} | {edge.end for edge in edges})
        for start, end in pairwise(breaks):
            if end - start <= GEOMETRY_TOLERANCE:
                continue
            midpoint = (start + end) / 2
            room_ids = sorted(
                {
                    edge.room_id
                    for edge in edges
                    if edge.start - GEOMETRY_TOLERANCE <= midpoint
                    <= edge.end + GEOMETRY_TOLERANCE
                }
            )
            if not room_ids:
                continue
            if len(room_ids) >= 2:
                kind = "interior"
            elif _is_exterior(orientation, line, layout.building_bounds):
                kind = "exterior"
            else:
                kind = "room_boundary"
            atomic.append(
                {
                    "orientation": orientation,
                    "line": line,
                    "start": start,
                    "end": end,
                    "kind": kind,
                    "room_ids": room_ids,
                }
            )
            if len(room_ids) > 2:
                issues.append(
                    {
                        "code": "AMBIGUOUS_WALL",
                        "severity": "error",
                        "message": "More than two rooms share the same wall segment.",
                        "suggestion": "Separate overlapping room edges and rebuild the topology.",
                        "room_ids": room_ids,
                    }
                )

    merged: list[dict[str, Any]] = []
    for segment in sorted(
        atomic,
        key=lambda item: (
            item["orientation"],
            item["line"],
            item["start"],
            item["end"],
            item["kind"],
            item["room_ids"],
        ),
    ):
        if (
            merged
            and merged[-1]["orientation"] == segment["orientation"]
            and merged[-1]["line"] == segment["line"]
            and merged[-1]["kind"] == segment["kind"]
            and merged[-1]["room_ids"] == segment["room_ids"]
            and abs(merged[-1]["end"] - segment["start"]) <= GEOMETRY_TOLERANCE
        ):
            merged[-1]["end"] = segment["end"]
        else:
            merged.append(dict(segment))

    walls = []
    for index, segment in enumerate(merged, start=1):
        if segment["orientation"] == "horizontal":
            x1, y1, x2, y2 = segment["start"], segment["line"], segment["end"], segment["line"]
        else:
            x1, y1, x2, y2 = segment["line"], segment["start"], segment["line"], segment["end"]
        walls.append(
            {
                "id": f"wall-{index}",
                "kind": segment["kind"],
                "orientation": segment["orientation"],
                "x1": _coordinate(x1),
                "y1": _coordinate(y1),
                "x2": _coordinate(x2),
                "y2": _coordinate(y2),
                "length_m": _coordinate(segment["end"] - segment["start"]),
                "room_ids": segment["room_ids"],
            }
        )
    return walls, issues


def _opening_geometry(wall: dict[str, Any], width: float, center_ratio: float = 0.5) -> dict[str, float]:
    length = float(wall["length_m"])
    edge_margin = 0.1
    width = min(width, max(MINIMUM_DOOR_WIDTH_M, length - 2 * edge_margin))
    center = max(
        width / 2 + edge_margin,
        min(length - width / 2 - edge_margin, length * center_ratio),
    )
    start = center - width / 2
    end = center + width / 2
    if wall["orientation"] == "horizontal":
        return {
            "x1": _coordinate(wall["x1"] + start),
            "y1": wall["y1"],
            "x2": _coordinate(wall["x1"] + end),
            "y2": wall["y2"],
        }
    return {
        "x1": wall["x1"],
        "y1": _coordinate(wall["y1"] + start),
        "x2": wall["x2"],
        "y2": _coordinate(wall["y1"] + end),
    }


def _door_priority(wall: dict[str, Any], rooms: dict[str, Room]) -> tuple[int, int, float]:
    room_types = [rooms[room_id].type for room_id in wall["room_ids"]]
    corridor_bonus = 1 if "corridor" in room_types else 0
    preference = PREFERRED_ADJACENCIES.get(frozenset(room_types), 0)
    return corridor_bonus, preference, float(wall["length_m"])


def _door_walls(
    walls: list[dict[str, Any]], rooms: dict[str, Room]
) -> tuple[list[dict[str, Any]], set[str]]:
    candidates = [
        wall
        for wall in walls
        if wall["kind"] == "interior"
        and len(wall["room_ids"]) == 2
        and wall["length_m"] >= MINIMUM_DOOR_WIDTH_M + 0.2
    ]
    graph: dict[str, set[str]] = defaultdict(set)
    for wall in candidates:
        first, second = wall["room_ids"]
        graph[first].add(second)
        graph[second].add(first)

    primary = next((room.id for room in rooms.values() if room.type == "corridor"), None)
    primary = primary or next((room.id for room in rooms.values() if room.type == "living"), None)
    primary = primary or next(iter(rooms), None)
    reachable: set[str] = set()
    if primary:
        queue = deque([primary])
        while queue:
            room_id = queue.popleft()
            if room_id in reachable:
                continue
            reachable.add(room_id)
            queue.extend(graph[room_id] - reachable)

    selected: list[dict[str, Any]] = []
    remaining = set(rooms)
    while remaining:
        component_root = primary if primary in remaining else min(remaining)
        visited = {component_root}
        remaining.remove(component_root)
        while True:
            connecting = [
                wall
                for wall in candidates
                if (wall["room_ids"][0] in visited) ^ (wall["room_ids"][1] in visited)
                and any(room_id in remaining for room_id in wall["room_ids"])
            ]
            if not connecting:
                break
            wall = max(connecting, key=lambda item: _door_priority(item, rooms))
            selected.append(wall)
            new_room = next(room_id for room_id in wall["room_ids"] if room_id not in visited)
            visited.add(new_room)
            remaining.discard(new_room)
    return selected, reachable


def build_topology(layout: Layout, accessibility: bool = False) -> dict[str, Any]:
    """Rebuild all semantic plan geometry from the current room rectangles."""

    walls, issues = _atomic_walls(layout)
    rooms = {room.id: room for room in layout.rooms}
    door_walls, reachable = _door_walls(walls, rooms)
    openings: list[dict[str, Any]] = []
    desired_door_width = 1.0 if accessibility else 0.9

    for wall in door_walls:
        width = min(desired_door_width, float(wall["length_m"]) - 0.2)
        openings.append(
            {
                "id": f"opening-{len(openings) + 1}",
                "kind": "door",
                "wall_id": wall["id"],
                "width_m": _coordinate(width),
                "room_ids": list(wall["room_ids"]),
                **_opening_geometry(wall, width),
            }
        )

    root_room = next((room for room in layout.rooms if room.type == "corridor"), None)
    root_room = root_room or next((room for room in layout.rooms if room.type == "living"), None)
    exterior_walls = [wall for wall in walls if wall["kind"] == "exterior"]
    entry_candidates = [
        wall for wall in exterior_walls if root_room and root_room.id in wall["room_ids"]
    ]
    if not entry_candidates:
        living_ids = {room.id for room in layout.rooms if room.type == "living"}
        entry_candidates = [
            wall for wall in exterior_walls if living_ids.intersection(wall["room_ids"])
        ]
    entry_wall = max(entry_candidates or exterior_walls, key=lambda wall: wall["length_m"], default=None)
    if entry_wall and entry_wall["length_m"] >= 1.2:
        entry_width = min(1.0, float(entry_wall["length_m"]) - 0.4)
        openings.append(
            {
                "id": f"opening-{len(openings) + 1}",
                "kind": "entry_door",
                "wall_id": entry_wall["id"],
                "width_m": _coordinate(entry_width),
                "room_ids": list(entry_wall["room_ids"]),
                **_opening_geometry(entry_wall, entry_width, 0.25),
            }
        )
    else:
        issues.append(
            {
                "code": "ENTRY_MISSING",
                "severity": "error",
                "message": "No exterior wall can accommodate an entry door.",
                "suggestion": "Move the living or corridor space to the building perimeter.",
                "room_ids": [root_room.id] if root_room else [],
            }
        )

    for room in sorted(layout.rooms, key=lambda item: item.id):
        if room.type not in HABITABLE_ROOM_TYPES:
            continue
        candidates = [wall for wall in exterior_walls if room.id in wall["room_ids"]]
        alternatives = [wall for wall in candidates if entry_wall is None or wall["id"] != entry_wall["id"]]
        window_wall = max(alternatives or candidates, key=lambda wall: wall["length_m"], default=None)
        if window_wall is None or window_wall["length_m"] < 1.4:
            issues.append(
                {
                    "code": "WINDOW_MISSING",
                    "severity": "warning",
                    "message": f"{room.label} has no exterior wall suitable for a concept window.",
                    "suggestion": "Move the room to the perimeter or add a verified light-well solution.",
                    "room_ids": [room.id],
                }
            )
            continue
        width = min(2.4, max(1.2, float(window_wall["length_m"]) * 0.35))
        width = min(width, float(window_wall["length_m"]) - 0.4)
        openings.append(
            {
                "id": f"opening-{len(openings) + 1}",
                "kind": "window",
                "wall_id": window_wall["id"],
                "width_m": _coordinate(width),
                "room_ids": [room.id],
                **_opening_geometry(window_wall, width, 0.65),
            }
        )

    disconnected = sorted(set(rooms) - reachable)
    if disconnected:
        issues.append(
            {
                "code": "TOPOLOGY_DISCONNECTED",
                "severity": "error",
                "message": f"{len(disconnected)} room(s) are disconnected from the door graph.",
                "suggestion": "Restore a shared wall connection or add a circulation zone.",
                "room_ids": disconnected,
            }
        )

    corridors = []
    for room in layout.rooms:
        if room.type != "corridor":
            continue
        corridors.append(
            {
                "id": f"corridor-{len(corridors) + 1}",
                "room_id": room.id,
                "x": room.x,
                "y": room.y,
                "width": room.width,
                "depth": room.depth,
                "door_ids": [
                    opening["id"]
                    for opening in openings
                    if opening["kind"] == "door" and room.id in opening["room_ids"]
                ],
            }
        )
    if not corridors:
        issues.append(
            {
                "code": "CORRIDOR_MISSING",
                "severity": "warning",
                "message": "The layout has no explicit corridor space.",
                "suggestion": "Regenerate the concept or reserve a circulation zone.",
                "room_ids": [],
            }
        )

    return {
        "version": 1,
        "walls": walls,
        "openings": openings,
        "corridors": corridors,
        "issues": issues,
        "summary": {
            "walls": len(walls),
            "doors": sum(opening["kind"] in {"door", "entry_door"} for opening in openings),
            "windows": sum(opening["kind"] == "window" for opening in openings),
            "corridors": len(corridors),
            "topology_issues": len(issues),
        },
    }
