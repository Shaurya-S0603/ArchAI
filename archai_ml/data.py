"""Program-only graph inputs and explicitly selected, integrity-checked targets."""

from collections import Counter
import json
import math
from pathlib import Path
from random import Random

import torch

from archai.datasets.pipeline import load_dataset
from archai.datasets.schema import ROOM_TYPES, SPLITS
from archai.services.layout_generator import PREFERRED_ADJACENCIES, ROOM_LIBRARY

FEATURE_COUNT = 7


def encode_programs(programs: list[dict]) -> dict:
    """No observed boxes, adjacency, sample IDs or split labels enter the encoder.

    Repeated room types use their order in the program as an instance index.
    Training uses the Phase 2C canonical type/geometry target ordering convention.
    """
    if not programs:
        raise ValueError("At least one room program is required.")
    for p in programs:
        if not isinstance(p, dict) or set(p) - {"footprint_m", "room_types", "desired_adjacency"}:
            raise ValueError("Unsupported program field; observed targets are not inputs.")
        types, footprint = p.get("room_types"), p.get("footprint_m")
        if not isinstance(types, list) or not 4 <= len(types) <= 32:
            raise ValueError("A program requires 4-32 room types.")
        if any(not isinstance(t, str) or t not in ROOM_TYPES for t in types):
            raise ValueError("Unsupported room type.")
        if (
            not isinstance(footprint, list) or len(footprint) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) or not 1e-6 < v <= 10000
                   for v in footprint)
        ):
            raise ValueError("Footprint must contain two positive finite metre dimensions.")
    size = max(len(p["room_types"]) for p in programs)
    count = len(programs)
    result = {
        "type_ids": torch.zeros(count, size, dtype=torch.long),
        "features": torch.zeros(count, size, FEATURE_COUNT),
        "desired_graph": torch.zeros(count, size, size),
        "room_mask": torch.zeros(count, size, dtype=torch.bool),
        "footprint_m": torch.tensor([p["footprint_m"] for p in programs], dtype=torch.float32),
    }
    for b, program in enumerate(programs):
        types, (w, h) = program["room_types"], program["footprint_m"]
        totals, seen = Counter(types), Counter()
        target_sum = sum(ROOM_LIBRARY[t]["target"] for t in types)
        for i, t in enumerate(types):
            seen[t] += 1
            result["type_ids"][b, i] = ROOM_TYPES.index(t) + 1
            result["room_mask"][b, i] = True
            result["features"][b, i] = torch.tensor([
                ROOM_LIBRARY[t]["minimum"] / (w * h),
                ROOM_LIBRARY[t]["target"] / target_sum,
                (seen[t] - 1) / max(totals[t] - 1, 1),
                totals[t] / 32, w / 80, h / 80, len(types) / 32,
            ])
        graph = result["desired_graph"][b]
        if "desired_adjacency" in program:
            edges = program["desired_adjacency"]
            if not isinstance(edges, list):
                raise ValueError("Desired adjacency must be a list of index pairs.")
            for edge in edges:
                if (not isinstance(edge, list) or len(edge) != 2
                        or any(type(i) is not int or not 0 <= i < len(types) for i in edge)
                        or edge[0] == edge[1]):
                    raise ValueError("Invalid desired adjacency pair.")
                i, j = edge
                graph[i, j] = graph[j, i] = 1
        else:
            for i, a in enumerate(types):
                for j in range(i + 1, len(types)):
                    weight = PREFERRED_ADJACENCIES.get(frozenset((a, types[j])), 0) / 5
                    if "corridor" in (a, types[j]):
                        weight = max(weight, 0.6)
                    graph[i, j] = graph[j, i] = weight
    return result


def collate(rows: list[dict]) -> dict:
    inputs = encode_programs([
        {"footprint_m": r["footprint_m"], "room_types": [x["type"] for x in r["rooms"]]}
        for r in rows
    ])
    b, n = inputs["room_mask"].shape
    boxes, adjacency = torch.zeros(b, n, 4), torch.zeros(b, n, n)
    for i, row in enumerate(rows):
        boxes[i, :len(row["rooms"])] = torch.tensor([r["box"] for r in row["rooms"]])
        for a, c in row["adjacency"]:
            adjacency[i, a, c] = adjacency[i, c, a] = 1
    return {"inputs": inputs, "boxes": boxes, "adjacency": adjacency,
            "ids": [r["id"] for r in rows]}


class TrainingData:
    """Validate once, then cache immutable rows; never silently mix splits."""

    def __init__(self, directory: Path):
        self.manifest, self.rows = load_dataset(Path(directory))
        source = json.loads((Path(directory) / "source.json").read_text())
        review = source.get("review", {})
        if any(review.get(k) is not True for k in
               ("training", "derivatives", "redistribution", "checkpoint_distribution", "privacy")):
            raise ValueError("Training requires an admitted source review.")
        self.source = source

    def select(self, split: str) -> list[dict]:
        if split not in SPLITS:
            raise ValueError("Select train, validation or test explicitly.")
        rows = [r for r in self.rows if r["split"] == split]
        if not rows:
            raise ValueError(f"The {split} split is empty.")
        return rows

    def batches(self, split: str, batch_size: int, seed: int | None = None):
        if type(batch_size) is not int or not 1 <= batch_size <= 1024:
            raise ValueError("Batch size must be between 1 and 1024.")
        rows = self.select(split)
        if seed is not None:
            Random(seed).shuffle(rows)
        for start in range(0, len(rows), batch_size):
            yield collate(rows[start:start + batch_size])
