"""Meaningful diversity, repeatability, grouping and the serving validation boundary."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from archai.evaluation.cohorts import phase2f_cohorts, program_key
from archai.evaluation.dataset import build_synthetic_cases
from archai.services.layout_generator import generate_layouts
from archai_ml import diversity
from archai_ml.diversity import reflow_variants, select_distinct, validate_concepts
from archai_ml.repair import _canonical, project_layout, validate_repaired


@pytest.fixture
def parent():
    brief = build_synthetic_cases(1, 8123)[0].brief
    template = generate_layouts(brief)[0]
    row = _canonical(template)
    proposal = {"room_types": [r["type"] for r in row["rooms"]],
                "boxes": [[.35, .35, .25, .25] for r in row["rooms"]]}
    return brief, proposal, project_layout(brief, proposal, template)


def test_reflow_preserves_coverage_and_produces_distinct_repeatable_plans(parent):
    brief, proposal, layout = parent
    variants = list(reflow_variants(brief, proposal, layout))
    assert len(variants) == 9
    assert [l.to_dict() for l in variants] == [l.to_dict() for l in reflow_variants(brief, proposal, layout)]
    selected, nodes = select_distinct(variants, .025)
    assert len(selected) == 5 and nodes <= 20000
    validate_concepts(selected, brief)
    for plan in variants:
        assert all(validate_repaired(plan, brief).values())
        b = plan.building_bounds
        boxes = [[(r.x-b["x"])/b["width"], (r.y-b["y"])/b["depth"],
                  r.width/b["width"], r.depth/b["depth"]] for r in plan.rooms]
        expected = sum(abs(v-p) for box, raw in zip(boxes, proposal["boxes"], strict=True)
                       for v, p in zip(box, raw, strict=True)) / (4 * len(boxes))
        assert plan.metrics["repair"]["coordinate_mae_displacement"] == pytest.approx(expected)


def test_shortfall_expands_and_already_complete_pool_does_not(parent, monkeypatch):
    brief, proposal, layout = parent
    diagnostics = {"failures": [], "returned": 1}
    monkeypatch.setattr(diversity, "repair_candidates", lambda *_: ([layout], diagnostics))
    first, info = diversity.diverse_candidates(brief, proposal)
    assert info["expanded"] > 0
    validate_concepts(first, brief)
    monkeypatch.setattr(diversity, "repair_candidates", lambda *_: (first, diagnostics))
    second, info = diversity.diverse_candidates(brief, proposal)
    assert second == first and info["expanded"] == 0


def test_selection_can_skip_greedy_anchor_and_respects_work_budget(monkeypatch):
    monkeypatch.setattr(diversity, "concept_distance", lambda a, b: 0 if 0 in (a, b) else 1)
    selected, _ = select_distinct(list(range(6)), .025)
    assert selected == [1, 2, 3, 4, 5]
    _, nodes = select_distinct(list(range(6)), .025, maximum_nodes=2)
    assert nodes <= 2


def test_serving_boundary_rejects_shortfall_duplicate_and_corrupt_geometry(parent):
    brief, proposal, layout = parent
    selected, _ = select_distinct(list(reflow_variants(brief, proposal, layout)), .025)
    for bad in (selected[:4], [selected[0]] * 5):
        with pytest.raises(ValueError):
            validate_concepts(bad, brief)
    bad = deepcopy(selected)
    bad[0].rooms[0].width = 999
    with pytest.raises(ValueError):
        validate_concepts(bad, brief)


def test_fresh_cohorts_are_fixed_and_separated_by_model_input():
    cohorts, manifest = phase2f_cohorts()
    assert manifest == json.loads(Path("data/benchmarks/phase2f-manifest.json").read_text())
    seen = {program_key(c.brief) for count, seed in ((100, 20260903), (120, 20260905), (1000, 20260907))
            for c in build_synthetic_cases(count, seed)}
    for cases in cohorts.values():
        keys = {program_key(c.brief) for c in cases}
        assert len(keys) == len(cases) and seen.isdisjoint(keys)
        seen.update(keys)
    brief = deepcopy(cohorts["development"][0].brief)
    original = program_key(brief)
    brief = replace(brief, site_width_m=brief.site_depth_m, site_depth_m=brief.site_width_m,
                    budget=brief.budget + 1000)
    assert program_key(brief) == original
