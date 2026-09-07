"""Repair guarantees, rejection, proposal influence and matched comparison evidence."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from archai.datasets.pilot import build_pilot
from archai.datasets.schema import geometry_key
from archai.evaluation.dataset import build_synthetic_cases
from archai.services.layout_generator import generate_layouts
from archai_ml import repair
from archai_ml.experiment import TrainConfig, train
from archai_ml.repair import (
    RepairConfig,
    concept_distance,
    project_layout,
    repair_candidates,
    validate_proposal,
    validate_repaired,
)
from archai_ml.repair_evaluation import (
    RepairedCandidate,
    main,
    raw_validity,
    run_comparison,
    stress,
)


@pytest.fixture
def example():
    brief = build_synthetic_cases(count=1, seed=98123)[0].brief
    template = generate_layouts(brief)[0]
    row = repair._canonical(template)
    proposal = {"room_types": [r["type"] for r in row["rooms"]],
                "boxes": [r["box"] for r in row["rooms"]]}
    return brief, template, proposal


def test_overlapping_proposal_is_repaired_reproducibly(example):
    brief, template, proposal = example
    proposal["boxes"] = [[.35, .35, .25, .25] for _ in proposal["boxes"]]
    assert not raw_validity(brief, proposal["boxes"])["no_overlap"]
    first = project_layout(brief, proposal, template)
    second = project_layout(brief, proposal, template)
    assert first.to_dict() == second.to_dict()
    assert all(validate_repaired(first, brief).values())
    assert first.metrics["repair"]["coordinate_mae_displacement"] > 0


def test_proposal_changes_assignment_without_observed_targets(example):
    brief, template, proposal = example
    config = RepairConfig(adjacency_reward=0, deterministic_limit=.1)
    first = project_layout(brief, proposal, template, config=config)
    changed = deepcopy(proposal)
    a, b = (proposal["room_types"].index(t) for t in ("living", "kitchen"))
    changed["boxes"][a], changed["boxes"][b] = changed["boxes"][b], changed["boxes"][a]
    second = project_layout(brief, changed, template, config=config)
    first_living = next(r for r in first.rooms if r.type == "living")
    second_living = next(r for r in second.rooms if r.type == "living")
    assert (first_living.x, first_living.y) != (second_living.x, second_living.y)


@pytest.mark.parametrize("change", [
    lambda p: p.update(room_types=[]), lambda p: p.update(boxes=[]),
    lambda p: p["boxes"][0].__setitem__(0, float("nan")),
    lambda p: p["boxes"][0].__setitem__(1, True),
    lambda p: p["boxes"][0].__setitem__(2, -1),
    lambda p: p["boxes"][0].__setitem__(0, 100),
    lambda p: p.update(target_adjacency=[]),
])
def test_bad_proposals_are_rejected(example, change):
    brief, template, proposal = example
    change(proposal)
    with pytest.raises(ValueError):
        project_layout(brief, proposal, template)


@pytest.mark.parametrize("change", [
    {"deterministic_limit": 0}, {"adjacency_reward": True}, {"passes": 0},
    {"minimum_separation": float("nan")},
])
def test_bad_repair_config_rejected(change):
    with pytest.raises(ValueError):
        replace(RepairConfig(), **change).validate()


def test_strict_gate_rejects_geometry_and_program_corruption(example):
    brief, template, proposal = example
    good = project_layout(brief, proposal, template)
    changes = [
        lambda l: l.rooms.pop(), lambda l: setattr(l.rooms[0], "id", l.rooms[1].id),
        lambda l: l.building_bounds.update(width=999),
        lambda l: setattr(l.rooms[0], "x", float("nan")),
        lambda l: setattr(l.rooms[0], "width", 1),
        lambda l: setattr(l.rooms[0], "x", -10),
    ]
    for change in changes:
        broken = deepcopy(good)
        change(broken)
        with pytest.raises(ValueError):
            validate_repaired(broken, brief)
    broken = deepcopy(good)
    room = next(r for r in broken.rooms if r.type == "living")
    room.width = room.depth = 1.8
    with pytest.raises(ValueError, match="minimum area"):
        validate_repaired(broken, brief)
    broken = deepcopy(good)
    a, b = broken.rooms[:2]
    b.x, b.y = a.x, a.y
    with pytest.raises(ValueError, match="overlap"):
        validate_repaired(broken, brief)
    broken = deepcopy(good)
    room = max(broken.rooms, key=lambda r: r.area)
    room.width -= .001
    with pytest.raises(ValueError, match="cover"):
        validate_repaired(broken, brief)


@pytest.mark.parametrize("omit,reason", [("entry_door", "entry"), ("door", "disconnected"),
                                        ("window", "window")])
def test_actual_topology_is_required(example, monkeypatch, omit, reason):
    brief, template, proposal = example
    good = project_layout(brief, proposal, template)
    real = repair.build_topology

    def without(layout, accessibility=False):
        topology = real(layout, accessibility)
        topology["openings"] = [o for o in topology["openings"] if o["kind"] != omit]
        return topology

    monkeypatch.setattr(repair, "build_topology", without)
    with pytest.raises(ValueError, match=reason):
        validate_repaired(good, brief)


def test_stale_topology_is_rebuilt_and_compliance_checked(example, monkeypatch):
    brief, template, proposal = example
    good = project_layout(brief, proposal, template)
    good.topology = {"openings": [], "issues": []}
    assert validate_repaired(good, brief)["door_connectivity"]
    monkeypatch.setattr(repair, "analyze_compliance", lambda *a: {"summary": {"errors": 1}})
    with pytest.raises(ValueError, match="compliance"):
        validate_repaired(good, brief)


def test_solver_unknown_and_no_valid_result_never_fall_back(example, monkeypatch):
    brief, template, proposal = example
    cp = repair._cp_model_module()

    class Unknown:
        parameters = SimpleNamespace()

        def solve(self, model):
            return cp.UNKNOWN

        def status_name(self, status):
            return "UNKNOWN"

    monkeypatch.setattr(repair, "_cp_model_module", lambda: SimpleNamespace(
        CpModel=cp.CpModel, CpSolver=Unknown, OPTIMAL=cp.OPTIMAL, FEASIBLE=cp.FEASIBLE))
    with pytest.raises(ValueError, match="UNKNOWN"):
        project_layout(brief, proposal, template)
    with pytest.raises(ValueError, match="No validated"):
        repair_candidates(brief, proposal, RepairConfig(passes=1))


def test_templates_must_match_request(example):
    brief, template, proposal = example
    template.building_bounds["width"] += 1
    with pytest.raises(ValueError, match="footprint"):
        project_layout(brief, proposal, template)
    with pytest.raises(ValueError):
        validate_proposal(brief, None)


def test_matching_and_reflection_do_not_inflate_diversity(example):
    brief, template, proposal = example
    good = project_layout(brief, proposal, template)
    altered = deepcopy(good)
    altered.rooms.reverse()
    for i, room in enumerate(altered.rooms):
        room.id, room.label = f"new-{i}", "Renamed"
    assert concept_distance(good, altered) == 0
    bounds = good.building_bounds
    for room in altered.rooms:
        room.x = 2 * bounds["x"] + bounds["width"] - room.x - room.width
    assert concept_distance(good, altered) < 1e-12
    altered.rooms.pop()
    with pytest.raises(ValueError, match="programs"):
        concept_distance(good, altered)


def test_selection_returns_only_valid_distinct_concepts_and_reports_shortfall(example):
    brief, _, proposal = example
    selected, diagnostics = repair_candidates(brief, proposal, RepairConfig(passes=1))
    assert 1 <= len(selected) <= 5
    assert diagnostics["returned"] == len(selected)
    keys = {geometry_key(repair._canonical(l), 3) for l in selected}
    assert len(keys) == len(selected)
    for i, layout in enumerate(selected):
        assert all(validate_repaired(layout, brief).values())
        assert all(concept_distance(layout, other) >= .025 for other in selected[:i])
    selected, diagnostics = repair_candidates(
        brief, proposal, RepairConfig(passes=1, minimum_separation=1))
    assert len(selected) == 1 and diagnostics["diversity_shortfall"]


@pytest.fixture(scope="module")
def frozen_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("repair-model")
    build_pilot(root / "pilot", count=40)
    report = train(root / "pilot", root / "run", TrainConfig(epochs=1, hidden_size=8, layers=1))
    (root / "frozen.json").write_text(json.dumps({"training": report}))
    return root


def test_complete_comparison_cli_artifacts_and_frozen_binding(frozen_run, tmp_path, capsys):
    config = RepairConfig(passes=1)
    report = run_comparison(frozen_run / "run", tmp_path / "comparison", config,
                            limit=1, frozen=frozen_run / "frozen.json", stress_count=1)
    assert report["component_passed"]
    assert report["stress"]["cases"] == 1
    assert report["frozen_solver"] is None  # A partial sample cannot compare to all 100 solver cases.
    assert (tmp_path / "comparison/preview.png").read_bytes().startswith(b"\x89PNG")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(asdict(config)))
    assert main(["--run", str(frozen_run / "run"), "--output", str(tmp_path / "cli"),
                 "--config", str(config_path), "--frozen", str(frozen_run / "frozen.json"),
                 "--limit", "1", "--enforce"]) == 0
    assert "component_passed" in capsys.readouterr().out
    with pytest.raises(ValueError, match="already exists"):
        run_comparison(frozen_run / "run", tmp_path / "cli", config)
    with pytest.raises(ValueError, match="limit"):
        run_comparison(frozen_run / "run", tmp_path / "bad-limit", config, limit=0)
    with pytest.raises(ValueError, match="frozen"):
        run_comparison(frozen_run / "run", tmp_path / "wrong-model", config, limit=1)
    with pytest.raises(SystemExit) as exc:
        main(["--run", str(frozen_run / "run"), "--output", str(tmp_path / "bad-cli"),
              "--config", str(config_path), "--limit", "0"])
    assert exc.value.code == 2


def test_failures_are_recorded_and_stress_rejects_bad_counts(frozen_run, monkeypatch):
    from archai_ml import repair_evaluation

    candidate = RepairedCandidate(frozen_run / "run", RepairConfig(passes=1))

    def reject(*args):
        raise ValueError("infeasible fixture")

    monkeypatch.setattr(repair_evaluation, "repair_candidates", reject)
    result = stress(candidate, 1)
    assert result["failed_cases"] == 1 and result["strict_validated_rate"] == 0
    assert candidate.history[0]["error"] == "infeasible fixture"
    with pytest.raises(ValueError, match="Stress count"):
        stress(candidate, 0)
