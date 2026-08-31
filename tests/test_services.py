from archai.models import DesignBrief
from archai.services.layout_generator import ROOM_LIBRARY, generate_layouts


def test_generation_is_deterministic(brief):
    design_brief = DesignBrief.from_dict(brief)
    first = [layout.to_dict() for layout in generate_layouts(design_brief)]
    second = [layout.to_dict() for layout in generate_layouts(design_brief)]
    assert first == second


def test_generated_rooms_fill_building_footprint(brief):
    design_brief = DesignBrief.from_dict(brief)
    for layout in generate_layouts(design_brief):
        footprint = layout.building_bounds["width"] * layout.building_bounds["depth"]
        assert abs(layout.floor_area - footprint) < 0.2


def test_documented_bedroom_rule_is_nine_square_metres():
    assert ROOM_LIBRARY["bedroom"]["minimum"] == 9.0
