"""Geometry objective masking, reproducibility, integrity and matched evaluation."""

import json
import shutil
from copy import deepcopy

import pytest

torch = pytest.importorskip("torch")

from archai.datasets.conditioning import prepare_conditioning_data
from archai.datasets.conditioning import read_protocol as data_protocol
from archai.datasets.schema import digest
from archai_ml import geometry
from archai_ml.conditioning import load_conditioned_run, train_conditioned
from archai_ml.experiment import TrainConfig


def test_worst_collision_masks_padding_self_pairs_and_has_finite_gradient():
    boxes = torch.tensor([[[0., 0., .5, .5], [.25, 0., .5, .5], [0., 0., 1., 1.]]],
                         requires_grad=True)
    mask = torch.tensor([[True, True, False]])
    value = geometry.worst_overlap(boxes, mask)
    assert float(value.detach()) == pytest.approx(.125)
    value.mean().backward()
    assert torch.isfinite(boxes.grad).all()
    assert boxes.grad[0, 2].count_nonzero() == 0
    assert boxes.grad[0, :2].count_nonzero() > 0
    perm = torch.tensor([2, 0, 1])
    assert torch.equal(value, geometry.worst_overlap(boxes[:, perm], mask[:, perm]))
    alone = torch.tensor([[True, False, False]])
    assert geometry.worst_overlap(boxes, alone).item() == 0
    separated = torch.tensor([[[0., 0., .5, .5], [.5, 0., .5, .5]]])
    assert geometry.worst_overlap(separated, mask[:, :2]).item() == 0


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("geometry")
    source = deepcopy(data_protocol())
    for split, count in (("train", 6), ("validation", 2), ("test", 2)):
        source["cohorts"][split]["count"] = count
    prepare_conditioning_data(root / "data", source)
    data = geometry.DevelopmentData(root / "data")
    protocol = geometry.read_protocol()
    protocol.update(data_protocol_digest=digest(source),
                    records_digest=data.manifest["records_digest"], bootstrap_samples=100)
    protocol["training"].update(epochs=2, hidden_size=16, layers=2, batch_size=64)
    config = TrainConfig(seed=20260912, **protocol["training"])
    reports = {arm: geometry.train_run(root / "data", root / arm, config, arm, protocol)
               for arm in ("base", "geometry")}
    return root, protocol, config, reports


def test_base_reproduces_frozen_training_and_holdout_cannot_be_selected(pair, tmp_path):
    root, protocol, config, reports = pair
    legacy = train_conditioned(root / "data", tmp_path / "legacy", config)
    assert legacy["state_digest"] == reports["base"]["state_digest"]
    assert legacy["validation"] == reports["base"]["validation"]
    assert reports["base"]["initial_state_digest"] == reports["geometry"]["initial_state_digest"]
    repeated = geometry.train_run(root / "data", tmp_path / "repeat", config, "geometry", protocol)
    assert repeated["state_digest"] == reports["geometry"]["state_digest"]
    assert repeated["test_evaluated"] is False and repeated["production_ready"] is False
    data = geometry.checked_data(root / "data", protocol)
    with pytest.raises(ValueError, match="reserved holdout"):
        data.select("test")
    with pytest.raises(ValueError, match="reserved holdout"):
        list(data.batches("test"))
    with pytest.raises(ValueError, match="identity"):
        geometry.checked_data(root / "data", {**protocol, "records_digest": "wrong"})
    with pytest.raises(ValueError, match="already exists"):
        geometry.train_run(root / "data", tmp_path / "repeat", config, "geometry", protocol)
    with pytest.raises(ValueError, match="declared arm"):
        geometry.train_run(root / "data", tmp_path / "invalid", config, "invalid", protocol)


def test_checkpoint_rejects_tampering_wrong_identity_and_legacy_loader(pair, tmp_path):
    root, protocol, _, reports = pair
    identity = reports["base"]["data_identity"]
    model, report = geometry.load_run(root / "geometry", identity, digest(protocol))
    assert not model.training and report["arm"] == "geometry"
    with pytest.raises(ValueError, match="version/data/protocol"):
        geometry.load_run(root / "geometry", identity, "wrong")
    with pytest.raises(ValueError, match="version"):
        load_conditioned_run(root / "geometry")
    shutil.copytree(root / "geometry", tmp_path / "bad")
    (tmp_path / "bad/weights.pt").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        geometry.load_run(tmp_path / "bad", identity, digest(protocol))


def test_real_four_arm_comparison_and_cli_keep_failed_research_visible(pair, tmp_path, monkeypatch):
    root, protocol, _, _ = pair
    monkeypatch.setattr(geometry, "read_protocol", lambda: protocol)
    status = geometry.main(["compare", "--data", str(root / "data"), "--runs", str(root),
                            "--output", str(tmp_path / "comparison"), "--enforce"])
    report = json.loads((tmp_path / "comparison/report.json").read_text())
    assert status == 0 and report["engineering_passed"]
    assert len(report["results"]) == 4 and len(report["paired_adjacency"]) == 3
    assert all(v["diagnostics"]["solver_attempts"] == 20 for v in report["results"].values())
    assert report["test_evaluated"] is False and report["qualified_model_release"] is False
    assert report["development_signal_passed"] == all(report["research_gates"].values())
    with pytest.raises(ValueError, match="already exists"):
        geometry.compare(root / "data", root, tmp_path / "comparison", protocol)
    with pytest.raises(ValueError, match="already exists"):
        geometry.main(["train-pair", "--data", str(root / "data"), "--output", str(root),
                       "--seed", "20260912"])


def test_compare_rejects_wrong_pair(pair, tmp_path):
    root, protocol, _, _ = pair
    for arm in ("base", "geometry"):
        shutil.copytree(root / "base", tmp_path / arm)
    with pytest.raises(ValueError, match="pair must share"):
        geometry.compare(root / "data", tmp_path, tmp_path / "out", protocol)
