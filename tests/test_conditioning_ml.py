"""Paired-model integrity, masking, control removal and actual matched repair."""

from copy import deepcopy
from dataclasses import replace

import pytest

torch = pytest.importorskip("torch")

from archai.datasets.conditioning import prepare_conditioning_data, read_protocol
from archai.evaluation.dataset import build_synthetic_cases
from archai_ml import benefit
from archai_ml.benefit import MatchedCandidate, paired_adjacency, repair_proposals, run_benefit
from archai_ml.conditioning import (
    ConceptGraphModel,
    ConceptTypeReference,
    ConditioningData,
    load_conditioned_run,
    train_conditioned,
)
from archai_ml.data import encode_programs
from archai_ml.experiment import TrainConfig, deterministic_cpu, load_run, state_digest
from archai_ml.model import RoomGraphModel
from archai_ml.repair import RepairConfig


@pytest.fixture(scope="module")
def experiment(tmp_path_factory):
    root = tmp_path_factory.mktemp("conditioned")
    protocol = deepcopy(read_protocol())
    protocol["cohorts"]["train"]["count"] = 6
    protocol["cohorts"]["validation"]["count"] = 2
    protocol["cohorts"]["test"]["count"] = 2
    protocol["training"].update(epochs=2, hidden_size=16, layers=2, batch_size=64)
    protocol["training_seeds"] = [20260912]
    protocol["bootstrap_samples"] = 100
    prepare_conditioning_data(root / "data", protocol)
    config = TrainConfig(seed=20260912, **protocol["training"])
    for name, flag in (("conditioned", True), ("unconditioned", False)):
        train_conditioned(root / "data", root / name, config, flag, progress=True)
    return root, protocol, config


def test_initial_capacity_ablation_and_padded_context_are_fair():
    program = {"room_types": ["bathroom", "bedroom", "corridor", "kitchen", "living"],
               "footprint_m": [15, 20]}
    inputs = encode_programs([program, {**program, "room_types": program["room_types"] + ["study"]}])
    inputs["concept_ids"] = torch.tensor([0, 1])
    deterministic_cpu(4)
    first = ConceptGraphModel(16, 2, True)
    deterministic_cpu(4)
    second = ConceptGraphModel(16, 2, False)
    assert state_digest(first) == state_digest(second)
    assert torch.equal(first(inputs)["boxes"], second(inputs)["boxes"])
    with torch.no_grad():
        first.concepts.weight[1].fill_(1)
        second.load_state_dict(first.state_dict())
    assert not torch.equal(first(inputs)["boxes"][1], second(inputs)["boxes"][1])
    assert first(inputs)["boxes"][0, -1].count_nonzero() == 0
    changed = {**inputs, "concept_ids": torch.tensor([4, 4])}
    assert torch.equal(second(inputs)["boxes"], second(changed)["boxes"])
    legacy = RoomGraphModel(16, 2)
    legacy.load_state_dict(first.graph.state_dict())
    assert torch.equal(legacy(inputs)["boxes"], legacy(inputs, None)["boxes"])


@pytest.mark.parametrize("ids", [None, [0], torch.tensor([True]), torch.tensor([-1]),
                                torch.tensor([5]), torch.tensor([[1]])])
def test_invalid_context_rejected(ids):
    model = ConceptGraphModel(8, 1)
    inputs = encode_programs([{"room_types": ["bathroom", "bedroom", "kitchen", "living"],
                               "footprint_m": [10, 10]}])
    inputs["concept_ids"] = ids
    with pytest.raises(ValueError, match="Concept IDs"):
        model(inputs)


def test_inputs_do_not_contain_geometry_and_reference_is_train_only(experiment):
    root, _, _ = experiment
    data = ConditioningData(root / "data")
    first = next(data.batches("train", 32))
    reference = ConceptTypeReference.fit(data)
    for row in data.rows:
        if row["split"] != "train":
            row["rooms"][0]["box"] = [0, 0, .1, .1]
    assert reference == ConceptTypeReference.fit(data)
    for row in data.rows:
        for room in row["rooms"]:
            room["box"] = [0, 0, .2, .2]
        row["adjacency"] = []
    changed = next(data.batches("train", 32))
    for key in first["inputs"]:
        assert torch.equal(first["inputs"][key], changed["inputs"][key])
    assert not torch.equal(first["boxes"], changed["boxes"])
    with pytest.raises(ValueError):
        list(data.batches("train", 0))
    with pytest.raises(ValueError):
        data.select("all")


def test_checkpoint_integrity_reproducibility_and_legacy_rejection(experiment, tmp_path):
    root, _, config = experiment
    model, report = load_conditioned_run(root / "conditioned")
    assert report["learning_passed"] and report["test_evaluated"] is False
    again = train_conditioned(root / "data", tmp_path / "again", config, True)
    assert again["state_digest"] == report["state_digest"]
    assert sum(p.numel() for p in model.parameters()) == report["parameters"]
    with pytest.raises(ValueError, match="already exists"):
        train_conditioned(root / "data", tmp_path / "again", config)
    with pytest.raises(ValueError, match="version"):
        load_run(root / "conditioned")
    with pytest.raises(ValueError, match="data mismatch"):
        load_conditioned_run(root / "conditioned", {"wrong": "identity"})
    (tmp_path / "again/weights.pt").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_conditioned_run(tmp_path / "again")


def test_matched_experiment_records_all_controls_and_does_not_score_holdout(experiment, tmp_path,
                                                                        monkeypatch):
    root, protocol, _ = experiment
    monkeypatch.setattr(benefit, "read_protocol", lambda: protocol)
    report = run_benefit(root / "data", root / "conditioned", root / "unconditioned", tmp_path / "out")
    assert report["engineering_passed"]
    assert report["test_evaluated"] is False and report["qualified_model_release"] is False
    assert len(report["results"]) == 4
    assert all(v["diagnostics"]["solver_attempts"] == 20 for v in report["results"].values())
    assert report["results"]["solver_only"]["diagnostics"]["mean_displacement"] is None
    assert benefit.main(["compare", "--data", str(root / "data"), "--runs", str(root),
                         "--output", str(tmp_path / "cli"), "--enforce"]) == 0
    with pytest.raises(ValueError, match="already exists"):
        run_benefit(root / "data", root / "conditioned", root / "unconditioned", tmp_path / "out")
    with pytest.raises(ValueError, match="paired arms"):
        run_benefit(root / "data", root / "unconditioned", root / "conditioned", tmp_path / "bad")


def test_solver_only_does_not_call_model_and_shortfalls_are_counted(monkeypatch):
    brief = build_synthetic_cases(1, 71924)[0].brief
    config = RepairConfig()
    def forbidden(*_):
        raise AssertionError("Solver-only control used a model")
    monkeypatch.setattr(benefit, "repair_proposals", lambda *a, **kw: ([], {
        "attempts": 10, "failures": ["infeasible"], "expanded": 0, "selection_nodes": 0}))
    candidate = MatchedCandidate(forbidden, config, solver_only=True)
    with pytest.raises(ValueError, match="five concepts"):
        candidate(brief)
    assert len(candidate.history) == 1 and candidate.history[0]["returned"] == 0
    assert benefit.summarize(candidate)["five_strict_distinct_rate"] == 0
    with pytest.raises(ValueError, match="five proposals"):
        repair_proposals(brief, [], config)


def test_paired_statistics_keep_failures_and_reject_unmatched_cases():
    def report(values):
        return {"dataset_sha256": "same", "cost_model_version": "v2",
                "cases": [{"case_id": str(i), "mean_adjacency_satisfaction": v}
                          for i, v in enumerate(values)]}
    first, second = report([1, 0]), report([.5, .5])
    result = paired_adjacency(first, second, samples=100)
    assert result["mean_delta"] == 0 and result["losses"] == result["wins"] == 1
    assert result["percentile_95_interval"][0] < 0 < result["percentile_95_interval"][1]
    assert result == paired_adjacency(first, second, samples=100)
    for altered in ({**second, "dataset_sha256": "other"},
                    {**second, "cost_model_version": "old"}, report([.5])):
        with pytest.raises(ValueError):
            paired_adjacency(first, altered, samples=100)


def test_cli_protocol_and_invalid_training_budget(experiment, tmp_path, monkeypatch):
    root, protocol, config = experiment
    monkeypatch.setattr(benefit, "read_protocol", lambda: protocol)
    with pytest.raises(ValueError, match="declared seed"):
        benefit.main(["train-pair", "--data", str(root / "data"), "--output", str(tmp_path / "p"),
                      "--seed", "999"])
    with pytest.raises(ValueError):
        train_conditioned(root / "data", tmp_path / "bad", replace(config, epochs=0))
    assert benefit.main(["train-pair", "--data", str(root / "data"), "--output", str(tmp_path / "pair"),
                         "--seed", str(config.seed)]) == 0
    with pytest.raises(ValueError, match="already exists"):
        benefit.main(["train-pair", "--data", str(root / "data"), "--output", str(tmp_path / "pair"),
                      "--seed", str(config.seed)])
