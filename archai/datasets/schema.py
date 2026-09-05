"""Strict metre-based rectangle adapter and canonical normalized room graphs."""

from __future__ import annotations

import hashlib
import json
import math
import re
from itertools import combinations

from archai.services.layout_generator import ROOM_LIBRARY

SCHEMA_VERSION = 1
ROOM_TYPES = tuple(sorted(ROOM_LIBRARY))
SPLITS = ("train", "validation", "test")
EPS = 1e-6
SNAP_METRES = 0.002


def encode(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


def identifier(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,100}", value):
        raise ValueError("invalid_identifier")
    return value


def number(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid_number")
    value = float(value)
    if not math.isfinite(value) or abs(value) > 10000:
        raise ValueError("invalid_number")
    return value


def rectangle(data) -> list[float]:
    if not isinstance(data, dict) or set(data) != {"x", "y", "width", "depth"}:
        raise ValueError("unsupported_rectangle")
    values = [number(data[k]) for k in ("x", "y", "width", "depth")]
    if min(values[2:]) <= EPS:
        raise ValueError("invalid_dimensions")
    return values


def _snap_edges(rooms: list[dict], width: float, depth: float) -> None:
    # The web generator rounds x/y and dimensions separately to millimetres.
    # Consolidate edge clusters spanning at most 2 mm (never an unbounded chain).
    # Footprint edges take precedence, then use a deterministic cluster mean.
    for axis, limit in ((0, width), (1, depth)):
        values = sorted(
            {0.0, limit}
            | {v for r in rooms for v in (r["box"][axis], r["box"][axis] + r["box"][axis + 2])}
        )
        clusters = []
        for value in values:
            if not clusters or value - clusters[-1][0] > SNAP_METRES + EPS:
                clusters.append([value])
            else:
                clusters[-1].append(value)
        mapping = {}
        for cluster in clusters:
            anchor = (
                0.0
                if 0.0 in cluster
                else limit
                if limit in cluster
                else sum(cluster) / len(cluster)
            )
            mapping.update({v: anchor for v in cluster})
        for room in rooms:
            start = room["box"][axis]
            end = start + room["box"][axis + 2]
            room["box"][axis] = mapping[start]
            room["box"][axis + 2] = mapping[end] - mapping[start]


def canonicalize(raw: dict) -> dict:
    """Reject unsupported geometry; never approximate polygons with bounding boxes.

    Shared-boundary edges are geometric targets, not observed doors. Input room
    labels, addresses and arbitrary metadata are deliberately not in this schema.
    """
    required = {"schema_version", "id", "building_id", "source_id", "units", "footprint", "rooms"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError("invalid_record_fields")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported_schema")
    if raw["units"] != "m":
        raise ValueError("unsupported_units")
    ids = {k: identifier(raw[k]) for k in ("id", "building_id", "source_id")}
    bx, by, bw, bh = rectangle(raw["footprint"])
    if not isinstance(raw["rooms"], list) or not 4 <= len(raw["rooms"]) <= 32:
        raise ValueError("unsupported_room_count")
    rooms, seen = [], set()
    for room in raw["rooms"]:
        if not isinstance(room, dict) or set(room) != {"id", "type", "box"}:
            raise ValueError("invalid_room_fields")
        rid = identifier(room["id"])
        if rid in seen:
            raise ValueError("duplicate_room_id")
        seen.add(rid)
        kind = room["type"]
        if not isinstance(kind, str) or kind not in ROOM_TYPES:
            raise ValueError("unsupported_room_type")
        x, y, w, h = rectangle(room["box"])
        if (
            x < bx - SNAP_METRES
            or y < by - SNAP_METRES
            or x + w > bx + bw + SNAP_METRES
            or y + h > by + bh + SNAP_METRES
        ):
            raise ValueError("outside_footprint")
        if w * h + EPS < ROOM_LIBRARY[kind]["minimum"]:
            raise ValueError("minimum_area")
        rooms.append({"type": kind, "box": [x - bx, y - by, w, h]})
    _snap_edges(rooms, bw, bh)
    for room in rooms:
        _, _, w, h = room["box"]
        if w <= EPS or h <= EPS or w * h + EPS < ROOM_LIBRARY[room["type"]]["minimum"]:
            raise ValueError("minimum_area_after_snap")
    # Ordering and IDs have no effect on canonical geometry or duplicate hashes.
    rooms.sort(key=lambda room: (room["type"], room["box"]))
    edges = []
    for i, j in combinations(range(len(rooms)), 2):
        x, y, w, h = rooms[i]["box"]
        a, b, c, d = rooms[j]["box"]
        dx, dy = min(x + w, a + c) - max(x, a), min(y + h, b + d) - max(y, b)
        if dx > EPS and dy > EPS:
            raise ValueError("overlap")
        touching = (abs(x + w - a) <= EPS or abs(a + c - x) <= EPS) and dy >= 0.8
        touching |= (abs(y + h - b) <= EPS or abs(b + d - y) <= EPS) and dx >= 0.8
        if touching:
            edges.append([i, j])
    reached = {0}
    while True:
        expanded = reached | {b for a, b in edges if a in reached}
        expanded |= {a for a, b in edges if b in reached}
        if expanded == reached:
            break
        reached = expanded
    if len(reached) != len(rooms):
        raise ValueError("disconnected_shared_boundary_graph")
    for room in rooms:
        x, y, w, h = room["box"]
        room["box"] = [round(x / bw, 8), round(y / bh, 8), round(w / bw, 8), round(h / bh, 8)]
    return {
        "schema_version": SCHEMA_VERSION,
        **ids,
        "footprint_m": [bw, bh],
        "rooms": rooms,
        "adjacency": edges,
    }


def geometry_key(record: dict, precision: int = 8) -> str:
    """Scale/translation/quarter-turn/reflection invariant bucket fingerprint.

    Coarse (3 decimal) keys catch approximate copies in the same rounding bins;
    this is not a comprehensive nearest-neighbor plagiarism detector.
    """
    variants = []
    for swap in (False, True):
        for flip_x in (False, True):
            for flip_y in (False, True):
                transformed = []
                for room in record["rooms"]:
                    x, y, w, h = room["box"]
                    if swap:
                        x, y, w, h = y, x, h, w
                    if flip_x:
                        x = 1 - x - w
                    if flip_y:
                        y = 1 - y - h
                    transformed.append([room["type"], *[round(v, precision) for v in (x, y, w, h)]])
                bw, bh = record["footprint_m"]
                aspect = bh / bw if swap else bw / bh
                variants.append(encode([round(aspect, precision), sorted(transformed)]))
    return hashlib.sha256(min(variants).encode()).hexdigest()


def validate_canonical(row: dict) -> None:
    """Revalidate decoded training targets, including graph indices and geometry."""
    expected = {
        "schema_version",
        "id",
        "building_id",
        "source_id",
        "footprint_m",
        "rooms",
        "adjacency",
        "group_id",
        "split",
    }
    if not isinstance(row, dict) or set(row) != expected:
        raise ValueError("Invalid canonical record fields.")
    if not isinstance(row["footprint_m"], list) or len(row["footprint_m"]) != 2:
        raise ValueError("Invalid canonical footprint.")
    bw, bh = [number(v) for v in row["footprint_m"]]
    if min(bw, bh) <= 0 or row["split"] not in SPLITS:
        raise ValueError("Invalid canonical footprint/split.")
    identifier(row["group_id"])
    rooms = []
    if not isinstance(row["rooms"], list):
        raise ValueError("Invalid canonical rooms.")
    for i, room in enumerate(row["rooms"]):
        if (
            not isinstance(room, dict)
            or set(room) != {"type", "box"}
            or not isinstance(room["box"], list)
            or len(room["box"]) != 4
        ):
            raise ValueError("Invalid canonical room.")
        x, y, w, h = [number(v) for v in room["box"]]
        if min(x, y) < 0 or min(w, h) <= 0 or x + w > 1 + EPS or y + h > 1 + EPS:
            raise ValueError("Invalid normalized box.")
        rooms.append(
            {
                "id": f"r{i}",
                "type": room["type"],
                "box": {"x": x * bw, "y": y * bh, "width": w * bw, "depth": h * bh},
            }
        )
    check = canonicalize(
        {
            "schema_version": row["schema_version"],
            "id": row["id"],
            "building_id": row["building_id"],
            "source_id": row["source_id"],
            "units": "m",
            "footprint": {"x": 0, "y": 0, "width": bw, "depth": bh},
            "rooms": rooms,
        }
    )
    if row["adjacency"] != check["adjacency"]:
        raise ValueError("Canonical adjacency does not match geometry.")
    for actual, rebuilt in zip(row["rooms"], check["rooms"], strict=True):
        if actual["type"] != rebuilt["type"] or any(
            abs(a - b) > 1e-7 for a, b in zip(actual["box"], rebuilt["box"], strict=True)
        ):
            raise ValueError("Noncanonical room order or coordinates.")
