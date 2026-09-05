"""Dependency-free, explicitly split-selected batches for future ML consumers."""

from random import Random

from archai.datasets.pipeline import load_dataset
from archai.datasets.schema import ROOM_TYPES, SPLITS
from archai.services.layout_generator import ROOM_LIBRARY


def batches(directory, split: str, batch_size: int = 16, seed: int | None = None):
    if split not in SPLITS or type(batch_size) is not int or not 1 <= batch_size <= 1024:
        raise ValueError("Select train/validation/test and a batch size between 1 and 1024.")
    _, rows = load_dataset(directory)
    selected = [r for r in rows if r["split"] == split]
    if seed is not None:
        Random(seed).shuffle(selected)
    for start in range(0, len(selected), batch_size):
        group = selected[start : start + batch_size]
        size = max(len(r["rooms"]) for r in group)
        batch = {
            k: []
            for k in (
                "ids",
                "footprint_m",
                "type_ids",
                "minimum_area_fraction",
                "room_mask",
                "target_boxes",
                "target_adjacency",
            )
        }
        for row in group:
            n = len(row["rooms"])
            bw, bh = row["footprint_m"]
            graph = [[0] * size for _ in range(size)]
            for a, b in row["adjacency"]:
                graph[a][b] = graph[b][a] = 1
            batch["ids"].append(row["id"])
            batch["footprint_m"].append([bw, bh])
            batch["type_ids"].append(
                [ROOM_TYPES.index(r["type"]) + 1 for r in row["rooms"]] + [0] * (size - n)
            )
            batch["minimum_area_fraction"].append(
                [ROOM_LIBRARY[r["type"]]["minimum"] / (bw * bh) for r in row["rooms"]]
                + [0] * (size - n)
            )
            batch["room_mask"].append([True] * n + [False] * (size - n))
            batch["target_boxes"].append(
                [r["box"][:] for r in row["rooms"]]
                + [[0.0, 0.0, 0.0, 0.0] for _ in range(size - n)]
            )
            batch["target_adjacency"].append(graph)
        yield batch
