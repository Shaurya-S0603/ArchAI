"""Optional ML tests. The web-only environment intentionally has no torch import."""

# ruff: noqa: E402 -- skip this optional module before importing its torch consumers.

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from archai.datasets.pilot import build_pilot
from archai_ml.__main__ import main
from archai_ml.data import TrainingData, collate, encode_programs
from archai_ml.experiment import (
    TrainConfig, TypeMeanReference, deterministic_cpu, evaluate_run, load_run,
    publish_directory, train,
)
from archai_ml.model import RoomGraphModel
from archai_ml.objective import evaluate, loss_terms


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    path = tmp_path_factory.mktemp("ml-data") / "pilot"
    build_pilot(path, count=40)
    return path


@pytest.fixture(scope="module")
def trained(dataset, tmp_path_factory):
    output = tmp_path_factory.mktemp("ml-runs") / "run"
    config = TrainConfig(epochs=3, hidden_size=16, layers=2, batch_size=64)
    return output, train(dataset, output, config, progress=True), config


def program():
    return {"footprint_m": [16.0, 20.0],
            "room_types": ["bathroom", "bedroom", "bedroom", "corridor", "kitchen", "living"]}


def test_inputs_are_program_only(dataset):
    row = TrainingData(dataset).select("train")[0]
    changed = deepcopy(row)
    changed["id"] = "different-id"
    changed["split"] = "test"
    changed["adjacency"] = []
    for room in changed["rooms"]:
        room["box"] = [0.1, 0.2, 0.3, 0.4]
    first, second = collate([row]), collate([changed])
    for key in first["inputs"]:
        assert torch.equal(first["inputs"][key], second["inputs"][key])
    assert not torch.equal(first["boxes"], second["boxes"])
    assert not torch.equal(first["adjacency"], second["adjacency"])


@pytest.mark.parametrize("change", [
    {"target_boxes": []}, {"footprint_m": [True, 20]}, {"footprint_m": [float("nan"), 20]},
    {"footprint_m": [0, 20]}, {"footprint_m": [1e300, 20]}, {"footprint_m": "16,20"},
    {"room_types": []}, {"room_types": ["unknown"] * 4},
    {"desired_adjacency": [[0, 99]]}, {"desired_adjacency": [[True, 2]]},
    {"desired_adjacency": [[0, 0]]}, {"desired_adjacency": "edges"},
])
def test_invalid_program_rejected(change):
    with pytest.raises(ValueError):
        encode_programs([{**program(), **change}])


def test_empty_and_explicit_graph_programs():
    with pytest.raises(ValueError):
        encode_programs([])
    p = {**program(), "desired_adjacency": [[0, 1], [1, 2]]}
    graph = encode_programs([p])["desired_graph"]
    assert graph.sum() == 4
    assert torch.equal(graph, graph.transpose(1, 2))


def test_graph_conditioning_padding_and_bounds():
    deterministic_cpu(13)
    model = RoomGraphModel(16, 4).eval()
    p = program()
    small = encode_programs([p])
    large = encode_programs([p, {**p, "room_types": p["room_types"] + ["study", "storage"]}])
    with torch.no_grad():
        first, padded = model(small), model(large)
        changed = model(encode_programs([{**p, "desired_adjacency": []}]))
    n = len(p["room_types"])
    assert torch.allclose(first["boxes"][0], padded["boxes"][0, :n], atol=1e-6)
    assert torch.allclose(first["adjacency_logits"][0],
                          padded["adjacency_logits"][0, :n, :n], atol=1e-6)
    assert not torch.allclose(first["boxes"], changed["boxes"])
    assert padded["boxes"][0, n:].count_nonzero() == 0
    assert torch.equal(first["adjacency_logits"], first["adjacency_logits"].transpose(1, 2))
    boxes = first["boxes"]
    assert (boxes >= 0).all() and (boxes[..., :2] + boxes[..., 2:] <= 1).all()


def test_masked_loss_and_gradients(dataset):
    rows = sorted(TrainingData(dataset).select("train"), key=lambda r: len(r["rooms"]))
    batch = collate([rows[0], rows[-1]])
    assert not batch["inputs"]["room_mask"].all()
    mask = batch["inputs"]["room_mask"]
    boxes = batch["boxes"].clone().requires_grad_()
    logits = torch.zeros_like(batch["adjacency"], requires_grad=True)
    first = loss_terms({"boxes": boxes, "adjacency_logits": logits}, batch)["loss"]
    first.backward()
    assert boxes.grad[~mask].count_nonzero() == 0
    invalid = ~(mask.unsqueeze(1) & mask.unsqueeze(2))
    invalid |= torch.eye(mask.shape[1], dtype=torch.bool)
    assert logits.grad[invalid].count_nonzero() == 0
    edited = {"boxes": boxes.detach().clone(), "adjacency_logits": logits.detach().clone()}
    edited["boxes"][~mask] = 100
    edited["adjacency_logits"][invalid] = 100
    assert torch.allclose(first, loss_terms(edited, batch)["loss"])


def test_model_can_fit_a_small_training_batch(dataset):
    deterministic_cpu(21)
    batch = collate([TrainingData(dataset).select("train")[0]])
    model = RoomGraphModel(16, 2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    initial = float(loss_terms(model(batch["inputs"]), batch)["loss"].detach())
    for _ in range(80):
        optimizer.zero_grad()
        loss = loss_terms(model(batch["inputs"]), batch)["loss"]
        loss.backward()
        optimizer.step()
    assert float(loss.detach()) < initial * 0.8


def test_metrics_distinguish_perfect_and_overlapping_geometry():
    row = {"id": "grid", "footprint_m": [10, 10], "adjacency": [[0, 1], [0, 2], [1, 3], [2, 3]],
           "rooms": [{"type": t, "box": b} for t, b in zip(
               ["bathroom", "bedroom", "kitchen", "living"],
               [[0, 0, .5, .5], [.5, 0, .5, .5], [0, .5, .5, .5], [.5, .5, .5, .5]],
               strict=True)]}
    batch = collate([row])
    data = SimpleNamespace(batches=lambda *args: [batch])

    class Fixed(torch.nn.Module):
        def __init__(self, boxes):
            super().__init__()
            self.boxes = boxes

        def forward(self, inputs):
            return {"boxes": self.boxes, "adjacency_logits": batch["adjacency"] * 40 - 20}

    perfect, _ = evaluate(Fixed(batch["boxes"]), data, "test")
    assert perfect["box_mae"] == 0 and perfect["mean_room_iou"] == 1
    assert perfect["adjacency_f1"] == 1 and perfect["geometric_valid_rate"] == 1
    broken = batch["boxes"].clone()
    broken[:, 1] = broken[:, 0]
    bad, _ = evaluate(Fixed(broken), data, "test")
    assert bad["no_overlap_rate"] == 0 and bad["geometric_valid_rate"] == 0
    broken[:] = float("nan")
    with pytest.raises(ValueError, match="Non-finite"):
        evaluate(Fixed(broken), data, "test")


def test_splits_and_reference_use_training_only(dataset):
    data = TrainingData(dataset)
    first = list(data.batches("train", 16, seed=4))
    second = list(data.batches("train", 16, seed=4))
    assert [b["ids"] for b in first] == [b["ids"] for b in second]
    train_ids = {r["id"] for r in data.select("train")}
    for split in ("validation", "test"):
        assert train_ids.isdisjoint(r["id"] for r in data.select(split))
    reference = TypeMeanReference.fit(data.select("train"))
    for r in data.rows:
        if r["split"] != "train":
            r["rooms"][0]["box"] = [0, 0, .1, .1]
    assert reference == TypeMeanReference.fit(data.select("train"))
    with pytest.raises(ValueError, match="explicitly"):
        data.select("all")
    with pytest.raises(ValueError, match="Batch size"):
        list(data.batches("train", 0))
    data.rows = data.select("train")
    with pytest.raises(ValueError, match="empty"):
        data.select("test")


@pytest.mark.parametrize("change", [{"seed": True}, {"epochs": 0}, {"layers": 0},
                                   {"hidden_size": 1000}, {"learning_rate": float("nan")}])
def test_invalid_training_config(change):
    with pytest.raises(ValueError):
        replace(TrainConfig(), **change).validate()


def test_reproducible_training_and_immutable_run(dataset, trained, tmp_path):
    run, report, config = trained
    again = train(dataset, tmp_path / "repeat", config)
    assert report == again
    assert report["research_gate_passed"] and not report["test_used_for_selection"]
    assert (run / "history.json").read_bytes() == (tmp_path / "repeat/history.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        train(dataset, run, config)
    with pytest.raises(ValueError, match="already exists"):
        publish_directory(run, {}, {})


def test_checkpoint_integrity_and_dataset_binding(trained, tmp_path):
    import shutil

    run, report, _ = trained
    model, loaded = load_run(run, report["dataset_digest"])
    assert loaded == report
    assert not model.training
    with pytest.raises(ValueError, match="dataset mismatch"):
        load_run(run, "another-dataset")
    copy = tmp_path / "copy"
    shutil.copytree(run, copy)
    (copy / "weights.pt").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        load_run(copy)
    manifest = json.loads((copy / "manifest.json").read_text())
    manifest["taxonomy"] = []
    (copy / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="taxonomy"):
        load_run(copy)
    manifest["taxonomy"] = json.loads((run / "manifest.json").read_text())["taxonomy"]
    manifest["files"]["other.pt"] = "0" * 64
    (copy / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="file manifest"):
        load_run(copy)


def test_training_source_permission_rechecked(dataset, tmp_path):
    import shutil

    copy = tmp_path / "source"
    shutil.copytree(dataset, copy)
    source = json.loads((copy / "source.json").read_text())
    source["review"]["training"] = False
    payload = json.dumps(source).encode()
    (copy / "source.json").write_bytes(payload)
    manifest = json.loads((copy / "manifest.json").read_text())
    manifest["files"]["source.json"] = hashlib.sha256(payload).hexdigest()
    (copy / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="admitted"):
        TrainingData(copy)


def test_held_out_evaluation_and_cli(dataset, trained, tmp_path, capsys):
    run, training, _ = trained
    report = evaluate_run(dataset, run, tmp_path / "evaluation", "test")
    assert report["metrics"]["plan_count"] == len(TrainingData(dataset).select("test"))
    assert report["state_digest"] == training["state_digest"]
    assert (tmp_path / "evaluation/preview.png").read_bytes().startswith(b"\x89PNG")
    assert main(["evaluate", "--dataset", str(dataset), "--run", str(run),
                 "--output", str(tmp_path / "cli-eval"), "--split", "validation"]) == 0
    path = tmp_path / "program.json"
    path.write_text(json.dumps(program()))
    assert main(["predict", "--run", str(run), "--program", str(path)]) == 0
    assert "raw research prediction" in capsys.readouterr().out
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"epochs": 1, "hidden_size": 8, "layers": 1}))
    assert main(["train", "--dataset", str(dataset), "--output", str(tmp_path / "cli-train"),
                 "--config", str(config)]) == 0
    path.write_text("{}")
    with pytest.raises(SystemExit) as exc:
        main(["predict", "--run", str(run), "--program", str(path)])
    assert exc.value.code == 2
