from archai.models import DesignBrief
from archai.services.layout_generator import generate_layouts
from archai.services.zoning import build_zones


def test_accessible_layouts_have_furniture_and_clearance_zones(brief):
    layout = generate_layouts(DesignBrief.from_dict(brief))[0]
    summary = layout.zones["summary"]

    assert summary["furniture_zones"] > 0
    assert summary["clearance_zones"] > 0
    assert summary["turning_circles"] == brief["bathrooms"] + 1
    assert summary["zoning_issues"] == 0


def test_all_zones_remain_inside_their_rooms(brief):
    layout = generate_layouts(DesignBrief.from_dict(brief))[0]
    rooms = {room.id: room for room in layout.rooms}
    for zone in [*layout.zones["furniture"], *layout.zones["clearances"]]:
        room = rooms[zone["room_id"]]
        if zone["shape"] == "circle":
            assert zone["cx"] - zone["radius"] >= room.x - 0.01
            assert zone["cy"] - zone["radius"] >= room.y - 0.01
            assert zone["cx"] + zone["radius"] <= room.x + room.width + 0.01
            assert zone["cy"] + zone["radius"] <= room.y + room.depth + 0.01
        else:
            assert zone["x"] >= room.x - 0.01
            assert zone["y"] >= room.y - 0.01
            assert zone["x"] + zone["width"] <= room.x + room.width + 0.01
            assert zone["y"] + zone["depth"] <= room.y + room.depth + 0.01


def test_non_accessible_zoning_omits_turning_circles(brief):
    brief["accessibility"] = False
    layout = generate_layouts(DesignBrief.from_dict(brief))[0]
    rebuilt = build_zones(layout, accessibility=False)

    assert rebuilt["summary"]["turning_circles"] == 0
    assert all(zone["kind"] != "turning_circle" for zone in rebuilt["clearances"])
