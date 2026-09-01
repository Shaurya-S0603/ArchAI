"""Derive concept furniture and accessibility-clearance zones."""

from __future__ import annotations

from typing import Any

from archai.models import Layout, Room

FURNITURE_PROGRAM: dict[str, tuple[tuple[str, str, float, float, float, float], ...]] = {
    "living": (
        ("sofa", "Sofa zone", 2.4, 0.9, 0.08, 0.12),
        ("coffee_table", "Coffee table", 1.2, 0.7, 0.62, 0.55),
    ),
    "kitchen": (
        ("counter", "Work counter", 2.4, 0.65, 0.08, 0.08),
        ("work_zone", "Kitchen work zone", 1.8, 1.2, 0.50, 0.55),
    ),
    "dining": (("dining_table", "Dining table", 1.8, 0.95, 0.50, 0.50),),
    "bedroom": (
        ("bed", "Bed zone", 2.0, 1.5, 0.50, 0.46),
        ("wardrobe", "Wardrobe", 1.5, 0.6, 0.08, 0.08),
    ),
    "bathroom": (("fixtures", "Fixture zone", 1.3, 0.8, 0.08, 0.08),),
    "study": (("desk", "Desk zone", 1.5, 0.7, 0.12, 0.12),),
    "garage": (("vehicle", "Vehicle bay", 2.6, 5.0, 0.50, 0.50),),
    "laundry": (("appliance", "Laundry appliances", 1.5, 0.7, 0.08, 0.08),),
    "balcony": (("outdoor_seating", "Outdoor seating", 1.5, 0.8, 0.50, 0.50),),
    "lounge": (("sofa", "Lounge seating", 2.2, 0.9, 0.50, 0.45),),
    "storage": (("shelving", "Storage shelving", 1.5, 0.6, 0.08, 0.08),),
    "utility": (("equipment", "Utility equipment", 1.4, 0.8, 0.08, 0.08),),
}


def _coordinate(value: float) -> float:
    return round(value, 3)


def _fitted_zone(
    room: Room,
    zone_id: str,
    kind: str,
    label: str,
    desired_width: float,
    desired_depth: float,
    x_ratio: float,
    y_ratio: float,
) -> dict[str, Any]:
    margin = min(0.3, room.width * 0.08, room.depth * 0.08)
    usable_width = max(0.4, room.width - 2 * margin)
    usable_depth = max(0.4, room.depth - 2 * margin)
    width = min(desired_width, usable_width)
    depth = min(desired_depth, usable_depth)
    x = room.x + margin + (usable_width - width) * x_ratio
    y = room.y + margin + (usable_depth - depth) * y_ratio
    return {
        "id": zone_id,
        "kind": kind,
        "label": label,
        "room_id": room.id,
        "shape": "rect",
        "x": _coordinate(x),
        "y": _coordinate(y),
        "width": _coordinate(width),
        "depth": _coordinate(depth),
        "rotation_deg": 0,
    }


def _door_approach_zone(
    room: Room,
    opening: dict[str, Any],
    index: int,
    accessibility: bool,
) -> dict[str, Any]:
    clearance_depth = 1.2 if accessibility else 0.9
    opening_width = max(float(opening["width_m"]), 1.2 if accessibility else 0.9)
    horizontal = abs(float(opening["y1"]) - float(opening["y2"])) < 0.01
    midpoint_x = (float(opening["x1"]) + float(opening["x2"])) / 2
    midpoint_y = (float(opening["y1"]) + float(opening["y2"])) / 2
    room_center_x = room.x + room.width / 2
    room_center_y = room.y + room.depth / 2
    if horizontal:
        width = min(room.width, opening_width)
        depth = min(room.depth, clearance_depth)
        x = max(room.x, min(room.x + room.width - width, midpoint_x - width / 2))
        y = midpoint_y - depth if room_center_y < midpoint_y else midpoint_y
    else:
        width = min(room.width, clearance_depth)
        depth = min(room.depth, opening_width)
        x = midpoint_x - width if room_center_x < midpoint_x else midpoint_x
        y = max(room.y, min(room.y + room.depth - depth, midpoint_y - depth / 2))
    x = max(room.x, min(room.x + room.width - width, x))
    y = max(room.y, min(room.y + room.depth - depth, y))
    return {
        "id": f"clearance-{index}",
        "kind": "door_approach",
        "label": "Accessible door approach" if accessibility else "Door approach",
        "room_id": room.id,
        "opening_id": opening["id"],
        "shape": "rect",
        "x": _coordinate(x),
        "y": _coordinate(y),
        "width": _coordinate(width),
        "depth": _coordinate(depth),
    }


def build_zones(layout: Layout, accessibility: bool = False) -> dict[str, Any]:
    """Create non-structural furniture and clearance overlays for a layout."""

    rooms = {room.id: room for room in layout.rooms}
    furniture = []
    for room in layout.rooms:
        for kind, label, width, depth, x_ratio, y_ratio in FURNITURE_PROGRAM.get(
            room.type, ()
        ):
            furniture.append(
                _fitted_zone(
                    room,
                    f"furniture-{len(furniture) + 1}",
                    kind,
                    label,
                    width,
                    depth,
                    x_ratio,
                    y_ratio,
                )
            )

    clearances = []
    for opening in layout.topology.get("openings", []):
        if opening.get("kind") not in {"door", "entry_door"}:
            continue
        for room_id in opening.get("room_ids", []):
            room = rooms.get(room_id)
            if room is None:
                continue
            clearances.append(
                _door_approach_zone(room, opening, len(clearances) + 1, accessibility)
            )

    issues = []
    if accessibility:
        turning_rooms = [
            room for room in layout.rooms if room.type in {"bathroom", "corridor"}
        ]
        for room in turning_rooms:
            if min(room.width, room.depth) + 0.01 < 1.5:
                issues.append(
                    {
                        "code": "TURNING_CLEARANCE_MISSING",
                        "severity": "warning",
                        "message": f"{room.label} cannot contain a 1.5 m concept turning circle.",
                        "suggestion": "Resize the room before detailed accessibility review.",
                        "room_ids": [room.id],
                    }
                )
                continue
            clearances.append(
                {
                    "id": f"clearance-{len(clearances) + 1}",
                    "kind": "turning_circle",
                    "label": "1.5 m turning circle",
                    "room_id": room.id,
                    "shape": "circle",
                    "cx": _coordinate(room.x + room.width / 2),
                    "cy": _coordinate(room.y + room.depth / 2),
                    "radius": 0.75,
                }
            )

    return {
        "version": 1,
        "furniture": furniture,
        "clearances": clearances,
        "issues": issues,
        "summary": {
            "furniture_zones": len(furniture),
            "clearance_zones": len(clearances),
            "turning_circles": sum(
                zone["kind"] == "turning_circle" for zone in clearances
            ),
            "zoning_issues": len(issues),
        },
    }
