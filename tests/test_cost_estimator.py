"""A fixed building envelope has one cost regardless of its interior partition."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from archai.database import get_db
from archai.evaluation.benchmark import evaluate_benchmark
from archai.evaluation.cohorts import phase2f_cohorts
from archai.evaluation.comparison import compare_reports
from archai.services.cost_estimator import estimate_cost
from archai.services.layout_generator import generate_layouts


def test_partition_rounding_cannot_change_budget_classification():
    case = phase2f_cohorts()[0]["development"][12]
    costs = [estimate_cost(l, case.brief) for l in generate_layouts(case.brief)]
    assert {c["estimated_total"] for c in costs} == {86911838.58}
    assert all(c["within_budget"] is False for c in costs)


def test_unassigned_and_overlapping_space_do_not_change_envelope_cost():
    brief = phase2f_cohorts()[0]["development"][0].brief
    layout = generate_layouts(brief)[0]
    original = estimate_cost(layout, brief)
    layout.rooms[0].width *= .5
    assert estimate_cost(layout, brief) == original
    layout.rooms[0].width *= 4
    assert estimate_cost(layout, brief) == original
    layout.building_bounds["width"] *= 2
    assert estimate_cost(layout, brief)["estimated_total"] == pytest.approx(
        original["estimated_total"] * 2, abs=.01)
    assert estimate_cost(layout, replace(brief, budget=0))["within_budget"] is None


def test_comparisons_reject_different_cost_semantics():
    cases = phase2f_cohorts()[0]["development"][:1]
    current = evaluate_benchmark(cases)
    old = deepcopy(current)
    old.pop("cost_model_version")
    with pytest.raises(ValueError, match="same cost model"):
        compare_reports(old, current)


def test_loading_saved_project_refreshes_legacy_cost_version(app, client, brief):
    generated = client.post("/api/v1/layouts/generate", json=brief).get_json()
    response = client.post("/api/v1/projects", json={
        "name": "Legacy quote", "brief": generated["brief"],
        "results": generated["results"], "active_index": 0})
    saved = response.get_json()["project"]
    old_results = deepcopy(saved["results"])
    for result in old_results:
        result["cost"].pop("cost_model_version")
        result["cost"]["estimated_total"] = 1
    with app.app_context():
        db = get_db()
        db.execute("UPDATE projects SET results_json = ? WHERE id = ?",
                   (json.dumps(old_results), saved["id"]))
        db.commit()
    loaded = client.get(f"/api/v1/projects/{saved['id']}").get_json()["project"]
    assert loaded["schema_version"] == saved["schema_version"] == 3
    assert [r["cost"] for r in loaded["results"]] == [r["cost"] for r in saved["results"]]
    assert [r["layout"]["rooms"] for r in loaded["results"]] == [
        r["layout"]["rooms"] for r in saved["results"]]
