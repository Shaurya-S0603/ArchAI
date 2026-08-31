"""Dependency-free OBJ export for concept massing models."""

from __future__ import annotations

from archai.models import Layout


def _box(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, int, int, int]],
    x: float,
    y: float,
    z: float,
    width: float,
    depth: float,
    height: float,
) -> None:
    start = len(vertices) + 1
    vertices.extend(
        [
            (x, z, y),
            (x + width, z, y),
            (x + width, z, y + depth),
            (x, z, y + depth),
            (x, z + height, y),
            (x + width, z + height, y),
            (x + width, z + height, y + depth),
            (x, z + height, y + depth),
        ]
    )
    faces.extend(
        [
            (start, start + 1, start + 2, start + 3),
            (start + 4, start + 7, start + 6, start + 5),
            (start, start + 4, start + 5, start + 1),
            (start + 1, start + 5, start + 6, start + 2),
            (start + 2, start + 6, start + 7, start + 3),
            (start + 4, start, start + 3, start + 7),
        ]
    )


def layout_to_obj(layout: Layout) -> str:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    groups: list[tuple[str, list[tuple[int, int, int, int]]]] = []
    lines = ["# ArchAI concept OBJ", f"# Layout: {layout.name}"]
    wall = 0.12
    wall_height = 2.8
    for room in layout.rooms:
        face_start = len(faces)
        _box(vertices, faces, room.x, room.y, 0, room.width, room.depth, 0.08)
        _box(vertices, faces, room.x, room.y, 0.08, room.width, wall, wall_height)
        _box(
            vertices, faces, room.x, room.y + room.depth - wall, 0.08, room.width, wall, wall_height
        )
        _box(vertices, faces, room.x, room.y, 0.08, wall, room.depth, wall_height)
        _box(
            vertices, faces, room.x + room.width - wall, room.y, 0.08, wall, room.depth, wall_height
        )
        groups.append((room.id, faces[face_start:]))

    lines.extend(f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in vertices)
    for room_id, room_faces in groups:
        lines.append(f"o {room_id}")
        lines.extend("f " + " ".join(str(index) for index in face) for face in room_faces)
    return "\n".join(lines) + "\n"
