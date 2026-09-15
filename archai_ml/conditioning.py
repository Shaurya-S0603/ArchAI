"""Concept-conditioned graph training and a same-capacity token-ablated control."""

import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path
from random import Random

import torch
from torch import nn

from archai.datasets.conditioning import VERSION, load_conditioning_data
from archai.datasets.schema import ROOM_TYPES, digest
from archai_ml.data import collate
from archai_ml.experiment import (
    TrainConfig,
    TypeMeanReference,
    code_identity,
    deterministic_cpu,
    json_bytes,
    publish_directory,
    state_digest,
)
from archai_ml.model import RoomGraphModel
from archai_ml.objective import evaluate, loss_terms


class ConditioningData:
    def __init__(self, directory):
        self.identity, self.manifest, self.context, self.rows = load_conditioning_data(directory)

    def select(self, split):
        if split not in ("train", "validation", "test"):
            raise ValueError("Select a conditioning split explicitly.")
        rows = [r for r in self.rows if r["split"] == split]
        if not rows:
            raise ValueError("Conditioning split is empty.")
        return rows

    def batches(self, split, batch_size=32, seed=None):
        if type(batch_size) is not int or not 1 <= batch_size <= 1024:
            raise ValueError("Invalid conditioning batch size.")
        rows = self.select(split)
        if seed is not None:
            Random(seed).shuffle(rows)
        for start in range(0, len(rows), batch_size):
            chosen = rows[start:start + batch_size]
            batch = collate(chosen)
            batch["inputs"]["concept_ids"] = torch.tensor(
                [self.context["concept_ids"][r["id"]] for r in chosen], dtype=torch.long)
            yield batch


def concept_ids(inputs):
    ids = inputs.get("concept_ids")
    if (not isinstance(ids, torch.Tensor) or ids.dtype != torch.long
            or ids.shape != (inputs["room_mask"].shape[0],)
            or (ids < 0).any() or (ids >= 5).any()):
        raise ValueError("Concept IDs must be one integer in 0-4 per program.")
    return ids


class ConceptGraphModel(nn.Module):
    """Both experiment arms have identical parameters and initial predictions.

The ablation replaces the independently selected concept token with zero. It
does not remove parameters, alter targets or receive a different training budget.
"""

    def __init__(self, hidden_size=64, layers=4, conditioned=True):
        super().__init__()
        if type(conditioned) is not bool:
            raise ValueError("Conditioned mode must be a boolean.")
        self.graph = RoomGraphModel(hidden_size, layers)
        self.concepts = nn.Embedding(5, hidden_size)
        nn.init.zeros_(self.concepts.weight)
        self.conditioned = conditioned

    def forward(self, inputs):
        ids = concept_ids(inputs)
        if not self.conditioned:
            ids = torch.zeros_like(ids)
        return self.graph(inputs, self.concepts(ids))


class ConceptTypeReference(nn.Module):
    """A strong cheap control: a training-only mean for each concept and type."""

    def __init__(self, states):
        super().__init__()
        self.boxes = torch.tensor([s["boxes"] for s in states])
        self.edges = torch.tensor([s["edge_logits"] for s in states])

    @staticmethod
    def fit(data):
        training = data.select("train")
        return [TypeMeanReference.fit([r for r in training
                                       if data.context["concept_ids"][r["id"]] == i] or training)
                for i in range(5)]

    def forward(self, inputs):
        context, types = concept_ids(inputs), inputs["type_ids"]
        return {"boxes": self.boxes[context[:, None], types],
                "adjacency_logits": self.edges[context[:, None, None],
                                               types.unsqueeze(2), types.unsqueeze(1)]}


def train_conditioned(data_directory, output, config, conditioned=True, progress=False):
    config.validate()
    if Path(output).exists():
        raise ValueError("Conditioned run already exists.")
    deterministic_cpu(config.seed)
    data = ConditioningData(data_directory)
    model = ConceptGraphModel(config.hidden_size, config.layers, conditioned)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    initial, _ = evaluate(model, data, "validation", config.batch_size)
    best, best_epoch = initial, 0
    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    history = []
    for epoch in range(1, config.epochs + 1):
        model.train()
        total, count = 0.0, 0
        for batch in data.batches("train", config.batch_size, seed=config.seed + epoch):
            optimizer.zero_grad(set_to_none=True)
            loss = loss_terms(model(batch["inputs"]), batch)["loss"]
            if not torch.isfinite(loss):
                raise ValueError("Non-finite conditioning loss; no checkpoint published.")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            total += float(loss.detach()) * len(batch["ids"])
            count += len(batch["ids"])
        validation, _ = evaluate(model, data, "validation", config.batch_size)
        history.append({"epoch": epoch, "train_loss": total / count, "validation": validation})
        if validation["loss"] < best["loss"]:
            best, best_epoch = validation, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        if progress and (epoch == 1 or epoch % 20 == 0):
            print(json.dumps({"conditioned": conditioned, "epoch": epoch,
                              "validation_loss": validation["loss"], "best_epoch": best_epoch}),
                  flush=True)
    model.load_state_dict(best_state)
    validation, predictions = evaluate(model, data, "validation", config.batch_size)
    states = ConceptTypeReference.fit(data)
    reference, _ = evaluate(ConceptTypeReference(states), data, "validation", config.batch_size)
    report = {"version": VERSION, "conditioned": conditioned, "config": asdict(config),
              "dataset_digest": data.manifest["records_digest"], "data_identity": data.identity,
              "protocol_digest": digest(data.context["protocol"]), "environment": code_identity(),
              "training_plans": len(data.select("train")),
              "validation_plans": len(data.select("validation")),
              "parameters": sum(p.numel() for p in model.parameters()), "best_epoch": best_epoch,
              "initial_validation": initial, "validation": validation, "reference": reference,
              "state_digest": state_digest(model), "test_evaluated": False,
              "learning_passed": best["loss"] < initial["loss"], "production_ready": False}
    weights = io.BytesIO()
    torch.save(model.state_dict(), weights)
    publish_directory(Path(output), {"weights.pt": weights.getvalue(),
                                    "training.json": json_bytes(report),
                                    "history.json": json_bytes(history),
                                    "reference.json": json_bytes(states),
                                    "validation-predictions.json": json_bytes(predictions)},
                      {"version": VERSION, "taxonomy": list(ROOM_TYPES),
                       "data_identity": data.identity})
    return report


def load_conditioned_run(directory, data_identity=None):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if (manifest.get("version") != VERSION or manifest.get("taxonomy") != list(ROOM_TYPES)
            or (data_identity is not None and manifest.get("data_identity") != data_identity)):
        raise ValueError("Conditioned checkpoint version/data mismatch.")
    expected = {"weights.pt", "training.json", "history.json", "reference.json",
                "validation-predictions.json"}
    if set(manifest.get("files", {})) != expected:
        raise ValueError("Invalid conditioned checkpoint file manifest.")
    for name, checksum in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("Conditioned checkpoint checksum mismatch.")
    report = json.loads((directory / "training.json").read_text())
    if report.get("version") != VERSION or report.get("data_identity") != manifest["data_identity"]:
        raise ValueError("Conditioned checkpoint metadata mismatch.")
    config = TrainConfig(**report["config"])
    config.validate()
    deterministic_cpu(config.seed)
    model = ConceptGraphModel(config.hidden_size, config.layers, report["conditioned"])
    model.load_state_dict(torch.load(directory / "weights.pt", map_location="cpu", weights_only=True))
    if (not all(torch.isfinite(t).all() for t in model.state_dict().values())
            or state_digest(model) != report["state_digest"]):
        raise ValueError("Conditioned checkpoint tensor integrity failure.")
    return model.eval(), report
