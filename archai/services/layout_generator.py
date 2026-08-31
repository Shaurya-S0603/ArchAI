"""Deterministic constraint-based residential floor-plan generator.

This is the transparent MVP baseline. It intentionally uses shape-grammar-like
rules and graph scoring before a trained model is introduced.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from math import hypot
from random import Random

from archai.models import DesignBrief, Layout, Room

ROOM_LIBRARY = {
    "living": {"label": "Living room", "target": 24.0, "minimum": 16.0, "color": "#9CC5A1"},
    "kitchen": {"label": "Kitchen", "target": 13.0, "minimum": 8.0, "color": "#E6B566"},
    "dining": {"label": "Dining", "target": 12.0, "minimum": 9.0, "color": "#F0CF8E"},
    "bedroom": {"label": "Bedroom", "target": 14.0, "minimum": 9.0, "color": "#9DB7D5"},
    "bathroom": {"label": "Bathroom", "target": 6.0, "minimum": 5.0, "color": "#8BC7C4"},
    "study": {"label": "Study", "target": 10.0, "minimum": 7.0, "color": "#B8A7D1"},
    "garage": {"label": "Garage", "target": 22.0, "minimum": 15.0, "color": "#AAB2B8"},
    "laundry": {"label": "Laundry", "target": 6.0, "minimum": 4.0, "color": "#B8CEC7"},
    "balcony": {"label": "Balcony", "target": 8.0, "minimum": 5.0, "color": "#BAD59D"},
    "lounge": {"label": "Lounge", "target": 15.0, "minimum": 10.0, "color": "#D0A5A5"},
    "storage": {"label": "Storage", "target": 5.0, "minimum": 3.0, "color": "#C5BBA8"},
    "utility": {"label": "Utility", "target": 6.0, "minimum": 4.0, "color": "#B5B9A4"},
}

VARIATIONS = (
    ("Balanced", "Balanced zoning and circulation", 11, 0.50),
    ("Social core", "Open shared spaces and kitchen-dining proximity", 23, 0.57),
    ("Private retreat", "Bedroom privacy and quieter circulation", 37, 0.44),
    ("Daylight first", "More habitable rooms along the building edge", 53, 0.62),
    ("Compact value", "Compact geometry to reduce envelope cost", 71, 0.48),
)

PREFERRED_ADJACENCIES = {
    frozenset(("kitchen", "dining")): 5,
    frozenset(("living", "dining")): 4,
    frozenset(("bedroom", "bathroom")): 3,
    frozenset(("garage", "utility")): 2,
}


@dataclass(frozen=True)
class RoomSpec:
    type: str
    label: str
    target_area: float
    minimum_area: float
    color: str


def _room_specs(brief: DesignBrief) -> list[RoomSpec]:
    room_types = ["living", "kitchen", "dining"]
    room_types.extend(["bedroom"] * brief.bedrooms)
    room_types.extend(["bathroom"] * brief.bathrooms)
    room_types.extend(brief.other_rooms)
    counts: Counter[str] = Counter()
    totals = Counter(room_types)
    specs: list[RoomSpec] = []
    for room_type in room_types:
        counts[room_type] += 1
        data = ROOM_LIBRARY[room_type]
        numbered = totals[room_type] > 1
        label = f"{data['label']} {counts[room_type]}" if numbered else str(data["label"])
        specs.append(
            RoomSpec(
                type=room_type,
                label=label,
                target_area=float(data["target"]),
                minimum_area=float(data["minimum"]),
                color=str(data["color"]),
            )
        )
    return specs


def _order_specs(specs: list[RoomSpec], variation_index: int, rng: Random) -> list[RoomSpec]:
    priorities = {
        0: {"living": 0, "dining": 1, "kitchen": 2, "bedroom": 3, "bathroom": 4},
        1: {"living": 0, "dining": 1, "kitchen": 2, "lounge": 3},
        2: {"bedroom": 0, "bathroom": 1, "study": 2, "living": 3},
        3: {"living": 0, "bedroom": 1, "study": 2, "kitchen": 3},
        4: {"garage": 0, "utility": 1, "kitchen": 2, "dining": 3},
    }[variation_index]
    decorated = [(priorities.get(spec.type, 5), rng.random(), spec) for spec in specs]
    decorated.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in decorated]


def _best_split(specs: list[RoomSpec], bias: float) -> int:
    total = sum(spec.target_area for spec in specs)
    running = 0.0
    best_index = 1
    best_distance = float("inf")
    for index, spec in enumerate(specs[:-1], start=1):
        running += spec.target_area
        distance = abs((running / total) - bias)
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index


def _partition(
    specs: list[RoomSpec],
    rect: tuple[float, float, float, float],
    depth: int,
    bias: float,
) -> list[tuple[RoomSpec, tuple[float, float, float, float]]]:
    if len(specs) == 1:
        return [(specs[0], rect)]

    x, y, width, height = rect
    split_index = _best_split(specs, bias if depth % 2 == 0 else 1 - bias)
    first, second = specs[:split_index], specs[split_index:]
    first_weight = sum(spec.target_area for spec in first)
    ratio = first_weight / sum(spec.target_area for spec in specs)

    vertical = width / max(height, 0.01) > 1.08
    if 0.92 <= width / max(height, 0.01) <= 1.08:
        vertical = depth % 2 == 0

    if vertical:
        first_width = width * ratio
        rect_a = (x, y, first_width, height)
        rect_b = (x + first_width, y, width - first_width, height)
    else:
        first_height = height * ratio
        rect_a = (x, y, width, first_height)
        rect_b = (x, y + first_height, width, height - first_height)

    return _partition(first, rect_a, depth + 1, bias) + _partition(second, rect_b, depth + 1, bias)


def shared_wall_length(room_a: Room, room_b: Room, tolerance: float = 0.04) -> float:
    a_right, b_right = room_a.x + room_a.width, room_b.x + room_b.width
    a_bottom, b_bottom = room_a.y + room_a.depth, room_b.y + room_b.depth
    vertical_touch = abs(a_right - room_b.x) <= tolerance or abs(b_right - room_a.x) <= tolerance
    horizontal_touch = (
        abs(a_bottom - room_b.y) <= tolerance or abs(b_bottom - room_a.y) <= tolerance
    )
    if vertical_touch:
        return max(0.0, min(a_bottom, b_bottom) - max(room_a.y, room_b.y))
    if horizontal_touch:
        return max(0.0, min(a_right, b_right) - max(room_a.x, room_b.x))
    return 0.0


def adjacency_pairs(rooms: Iterable[Room]) -> list[tuple[Room, Room, float]]:
    room_list = list(rooms)
    pairs = []
    for index, room_a in enumerate(room_list):
        for room_b in room_list[index + 1 :]:
            length = shared_wall_length(room_a, room_b)
            if length >= 0.8:
                pairs.append((room_a, room_b, length))
    return pairs


def _layout_metrics(layout: Layout) -> dict[str, float | int]:
    pairs = adjacency_pairs(layout.rooms)
    achieved = 0
    possible = 0
    circulation_distance = 0.0
    for room_a, room_b, _ in pairs:
        preference = PREFERRED_ADJACENCIES.get(frozenset((room_a.type, room_b.type)), 0)
        achieved += preference
        center_a = (room_a.x + room_a.width / 2, room_a.y + room_a.depth / 2)
        center_b = (room_b.x + room_b.width / 2, room_b.y + room_b.depth / 2)
        circulation_distance += hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
    for preference in PREFERRED_ADJACENCIES.values():
        possible += preference
    adjacency_score = min(100.0, 55.0 + (achieved / max(possible, 1)) * 45.0)
    compactness = layout.floor_area / max(
        layout.building_bounds["width"] * layout.building_bounds["depth"], 0.01
    )
    return {
        "adjacency_score": round(adjacency_score, 1),
        "compactness": round(compactness * 100, 1),
        "adjacency_count": len(pairs),
        "circulation_proxy_m": round(circulation_distance, 1),
    }


def generate_layouts(brief: DesignBrief) -> list[Layout]:
    specs = _room_specs(brief)
    margin_x = brief.site_width_m * 0.08
    margin_y = brief.site_depth_m * 0.08
    bounds = {
        "x": round(margin_x, 3),
        "y": round(margin_y, 3),
        "width": round(brief.site_width_m - 2 * margin_x, 3),
        "depth": round(brief.site_depth_m - 2 * margin_y, 3),
    }
    available_area = bounds["width"] * bounds["depth"]
    minimum_area = sum(spec.minimum_area for spec in specs)
    if minimum_area > available_area:
        raise ValueError(
            f"The requested rooms need at least {minimum_area:.0f} m², but the concept footprint "
            f"provides {available_area:.0f} m². Increase the site or remove rooms."
        )

    layouts: list[Layout] = []
    for index, (name, objective, seed, bias) in enumerate(VARIATIONS):
        rng = Random(seed + brief.bedrooms * 101 + brief.bathrooms * 17)
        ordered = _order_specs(specs, index, rng)
        assignments = _partition(
            ordered,
            (bounds["x"], bounds["y"], bounds["width"], bounds["depth"]),
            0,
            bias,
        )
        rooms = [
            Room(
                id=f"v{index + 1}-room-{room_index + 1}",
                type=spec.type,
                label=spec.label,
                x=round(rect[0], 3),
                y=round(rect[1], 3),
                width=round(rect[2], 3),
                depth=round(rect[3], 3),
                color=spec.color,
            )
            for room_index, (spec, rect) in enumerate(assignments)
        ]
        layout = Layout(
            id=f"archai-v{index + 1}",
            name=name,
            objective=objective,
            style=brief.style,
            site_width_m=brief.site_width_m,
            site_depth_m=brief.site_depth_m,
            building_bounds=dict(bounds),
            rooms=rooms,
        )
        layout.metrics = _layout_metrics(layout)
        layout.score = 0.65 * float(layout.metrics["adjacency_score"]) + 0.35 * float(
            layout.metrics["compactness"]
        )
        layouts.append(layout)

    return sorted(layouts, key=lambda layout: layout.score, reverse=True)
