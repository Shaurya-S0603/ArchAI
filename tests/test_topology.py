from collections import defaultdict, deque

from archai.models import DesignBrief
from archai.services.layout_generator import generate_layouts
from archai.services.topology import HABITABLE_ROOM_TYPES, build_topology


def _reachable_rooms(layout):
    graph = defaultdict(set)
    for opening in layout.topology["openings"]:
        if opening["kind"] != "door" or len(opening["room_ids"]) != 2:
            continue
        first, second = opening["room_ids"]
        graph[first].add(second)
        graph[second].add(first)
    corridor_id = next(room.id for room in layout.rooms if room.type == "corridor")
    visited = set()
    queue = deque([corridor_id])
    while queue:
        room_id = queue.popleft()
        if room_id in visited:
            continue
        visited.add(room_id)
        queue.extend(graph[room_id] - visited)
    return visited


def test_generated_layouts_have_complete_semantic_topology(brief):
    layouts = generate_layouts(DesignBrief.from_dict(brief))
    for layout in layouts:
        topology = layout.topology
        assert topology["version"] == 1
        assert topology["walls"]
        assert topology["summary"]["corridors"] == 1
        assert topology["summary"]["doors"] == len(layout.rooms) - 1 + 1
        assert topology["issues"] == []
        assert len({wall["id"] for wall in topology["walls"]}) == len(topology["walls"])
        assert all(wall["length_m"] > 0 for wall in topology["walls"])
        assert _reachable_rooms(layout) == {room.id for room in layout.rooms}


def test_habitable_rooms_receive_exterior_windows(brief):
    layout = generate_layouts(DesignBrief.from_dict(brief))[0]
    window_room_ids = {
        opening["room_ids"][0]
        for opening in layout.topology["openings"]
        if opening["kind"] == "window"
    }
    expected = {room.id for room in layout.rooms if room.type in HABITABLE_ROOM_TYPES}
    assert window_room_ids == expected
    assert any(opening["kind"] == "entry_door" for opening in layout.topology["openings"])


def test_topology_rebuilds_after_geometry_edit(brief):
    layout = generate_layouts(DesignBrief.from_dict(brief))[0]
    before = layout.topology
    edited_room = next(
        room
        for room in layout.rooms
        if room.type != "corridor" and abs(room.y - layout.building_bounds["y"]) < 0.01
    )
    edited_room.y += 0.5

    rebuilt = build_topology(layout, accessibility=True)

    assert rebuilt != before
    assert any(wall["kind"] == "room_boundary" for wall in rebuilt["walls"])
    wall_ids = {wall["id"] for wall in rebuilt["walls"]}
    assert all(opening["wall_id"] in wall_ids for opening in rebuilt["openings"])
