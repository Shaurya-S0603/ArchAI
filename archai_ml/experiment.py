"""Reproducible CPU training, immutable checkpoints and separate held-out evaluation."""

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import random
import shutil
import subprocess
import tempfile

import torch
from torch import nn

from archai.datasets.schema import ROOM_TYPES, digest, encode
from archai_ml import MODEL_VERSION
from archai_ml.data import TrainingData
from archai_ml.model import RoomGraphModel
from archai_ml.objective import evaluate, loss_terms


@dataclass(frozen=True)
class TrainConfig:
    seed: int = 20260906
    epochs: int = 120
    batch_size: int = 32
    hidden_size: int = 64
    layers: int = 4
    learning_rate: float = 0.002

    def validate(self):
        for key, low, high in (("seed", 0, 2**32 - 1), ("epochs", 1, 10000),
                               ("batch_size", 1, 1024), ("hidden_size", 8, 256), ("layers", 1, 8)):
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid training configuration: {key}.")
        rate = self.learning_rate
        if type(rate) not in (float, int) or not math.isfinite(rate) or not 0 < rate <= 0.1:
            raise ValueError("Invalid learning rate.")


def deterministic_cpu(seed):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def json_bytes(value):
    return (encode(value) + "\n").encode()


def publish_directory(destination: Path, files: dict[str, bytes], metadata: dict):
    """Only publish a complete, new directory; never overwrite an experiment."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Output already exists; choose a new run/evaluation directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".archai-ml-", dir=destination.parent))
    try:
        manifest = {**metadata, "files": {p: hashlib.sha256(b).hexdigest()
                                          for p, b in files.items()}}
        for name, content in {**files, "manifest.json": json_bytes(manifest)}.items():
            (stage / name).write_bytes(content)
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def code_identity():
    root = Path(__file__).resolve().parents[1]
    source = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for package in ("archai", "archai_ml") for p in sorted((root / package).rglob("*.py"))}
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                           stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    return {"git_revision": revision, "python_source_digest": digest(source),
            "python": platform.python_version(), "pytorch": str(torch.__version__),
            "platform": platform.platform(), "device": "cpu", "threads": 1}


class TypeMeanReference(nn.Module):
    """Train-only per-type box mean and smoothed pair-type adjacency frequency."""

    def __init__(self, state):
        super().__init__()
        self.boxes = torch.tensor(state["boxes"])
        self.edges = torch.tensor(state["edge_logits"])

    @staticmethod
    def fit(rows):
        size = len(ROOM_TYPES) + 1
        boxes, counts = torch.zeros(size, 4), torch.zeros(size)
        positives, pairs = torch.ones(size, size), torch.full((size, size), 2.0)
        for row in rows:
            types = [ROOM_TYPES.index(r["type"]) + 1 for r in row["rooms"]]
            adjacency = {tuple(e) for e in row["adjacency"]}
            for i, (t, room) in enumerate(zip(types, row["rooms"], strict=True)):
                boxes[t] += torch.tensor(room["box"])
                counts[t] += 1
                for j in range(i + 1, len(types)):
                    u = types[j]
                    for a, b in ((t, u), (u, t)):
                        pairs[a, b] += 1
                        positives[a, b] += (i, j) in adjacency
        # Unseen types use the training population mean, never held-out targets.
        overall = boxes.sum(0) / counts.sum()
        boxes = torch.where((counts > 0).unsqueeze(-1),
                            boxes / counts.clamp_min(1).unsqueeze(-1), overall)
        boxes[0] = 0
        probability = positives / pairs
        return {"boxes": boxes.tolist(), "edge_logits": torch.logit(probability).tolist()}

    def forward(self, inputs):
        ids = inputs["type_ids"]
        return {"boxes": self.boxes[ids],
                "adjacency_logits": self.edges[ids.unsqueeze(2), ids.unsqueeze(1)]}


def state_digest(model):
    return digest({k: v.detach().cpu().tolist() for k, v in model.state_dict().items()})


def train(dataset: Path, output: Path, config: TrainConfig, progress=False):
    config.validate()
    if Path(output).exists():
        raise ValueError("Output already exists; choose a new run directory.")
    deterministic_cpu(config.seed)
    data = TrainingData(dataset)
    train_rows, validation_rows = data.select("train"), data.select("validation")
    model = RoomGraphModel(config.hidden_size, config.layers)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    initial, _ = evaluate(model, data, "validation", config.batch_size)
    reference_state = TypeMeanReference.fit(train_rows)
    reference, _ = evaluate(TypeMeanReference(reference_state), data, "validation", config.batch_size)
    best_metrics, best_epoch = initial, 0
    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    history = []
    for epoch in range(1, config.epochs + 1):
        model.train()
        total, plans = 0.0, 0
        for batch in data.batches("train", config.batch_size, seed=config.seed + epoch):
            optimizer.zero_grad(set_to_none=True)
            loss = loss_terms(model(batch["inputs"]), batch)["loss"]
            if not torch.isfinite(loss):
                raise ValueError("Non-finite training loss; no checkpoint published.")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            total += float(loss.detach()) * len(batch["ids"])
            plans += len(batch["ids"])
        validation, _ = evaluate(model, data, "validation", config.batch_size)
        history.append({"epoch": epoch, "train_loss": total / plans, "validation": validation})
        if validation["loss"] < best_metrics["loss"]:
            best_metrics, best_epoch = validation, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        if progress and (epoch == 1 or epoch % 10 == 0 or epoch == config.epochs):
            print(encode({"epoch": epoch, "train_loss": total / plans,
                          "validation_loss": validation["loss"], "best_epoch": best_epoch}),
                  flush=True)
    model.load_state_dict(best_state)
    report = {
        "model_version": MODEL_VERSION, "config": asdict(config),
        "dataset_digest": data.manifest["records_digest"], "source_id": data.source["id"],
        "source_review": data.source["review"], "environment": code_identity(),
        "training_plans": len(train_rows), "validation_plans": len(validation_rows),
        "split_counts": dict(Counter(r["split"] for r in data.rows)),
        "training_groups": len({r["group_id"] for r in train_rows}),
        "validation_groups": len({r["group_id"] for r in validation_rows}),
        "parameters": sum(p.numel() for p in model.parameters()), "best_epoch": best_epoch,
        "initial_validation": initial, "best_validation": best_metrics,
        "reference_validation": reference, "state_digest": state_digest(model),
        "research_gate_passed": best_metrics["loss"] < initial["loss"],
        "test_used_for_selection": False, "production_ready": False,
    }
    checkpoint = io.BytesIO()
    torch.save(model.state_dict(), checkpoint)
    publish_directory(Path(output), {
        "weights.pt": checkpoint.getvalue(), "training.json": json_bytes(report),
        "history.json": json_bytes(history), "reference.json": json_bytes(reference_state),
    }, {"model_version": MODEL_VERSION, "taxonomy": list(ROOM_TYPES),
        "dataset_digest": data.manifest["records_digest"]})
    return report


def load_run(directory: Path, dataset_digest: str | None = None):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if (manifest.get("model_version") != MODEL_VERSION
            or manifest.get("taxonomy") != list(ROOM_TYPES)):
        raise ValueError("Unsupported checkpoint version or taxonomy.")
    if dataset_digest is not None and manifest.get("dataset_digest") != dataset_digest:
        raise ValueError("Checkpoint dataset mismatch.")
    if set(manifest.get("files", {})) != {"weights.pt", "training.json", "history.json", "reference.json"}:
        raise ValueError("Invalid checkpoint file manifest.")
    for name, expected in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Checkpoint checksum mismatch: {name}")
    report = json.loads((directory / "training.json").read_text())
    config = TrainConfig(**report["config"])
    config.validate()
    if report["dataset_digest"] != manifest["dataset_digest"]:
        raise ValueError("Checkpoint metadata mismatch.")
    deterministic_cpu(config.seed)
    model = RoomGraphModel(config.hidden_size, config.layers)
    state = torch.load(directory / "weights.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    if not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError("Checkpoint contains non-finite weights.")
    if state_digest(model) != report["state_digest"]:
        raise ValueError("Checkpoint tensor digest mismatch.")
    return model.eval(), report


def evaluate_run(dataset: Path, run: Path, output: Path, split: str):
    data = TrainingData(dataset)
    model, training = load_run(run, data.manifest["records_digest"])
    metrics, predictions = evaluate(model, data, split, training["config"]["batch_size"])
    reference = TypeMeanReference(json.loads((Path(run) / "reference.json").read_text()))
    reference_metrics, _ = evaluate(reference, data, split, training["config"]["batch_size"])
    report = {"model_version": MODEL_VERSION, "split": split, "metrics": metrics,
              "reference": reference_metrics, "dataset_digest": data.manifest["records_digest"],
              "state_digest": training["state_digest"], "best_epoch": training["best_epoch"],
              "environment": code_identity(), "production_ready": False,
              "unmet_release_gates": ["constraint repair and connected door/circulation topology",
                                      "four distinct valid concepts out of five",
                                      "1,000-brief stress test and CPU p95 below five seconds",
                                      "independent licensed real-plan evaluation",
                                      "blinded human preference above 60 percent"]}
    from archai_ml.preview import prediction_sheet

    publish_directory(Path(output), {"evaluation.json": json_bytes(report),
                                    "predictions.json": json_bytes(predictions),
                                    "preview.png": prediction_sheet(data.select(split), predictions)},
                      {"model_version": MODEL_VERSION, "dataset_digest": report["dataset_digest"],
                       "split": split})
    return report
