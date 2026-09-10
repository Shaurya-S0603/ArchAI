"""Room/pair masked losses and raw-geometry metrics; no repair is implied."""

import torch
from torch.nn import functional as F


def pair_mask(mask):
    return (mask.unsqueeze(1) & mask.unsqueeze(2)).triu(diagonal=1)


def intersections(boxes):
    lo, hi = boxes[..., :2], boxes[..., :2] + boxes[..., 2:]
    extent = (torch.minimum(hi.unsqueeze(2), hi.unsqueeze(1))
              - torch.maximum(lo.unsqueeze(2), lo.unsqueeze(1))).clamp_min(0)
    return extent.prod(-1)


def loss_terms(output, batch):
    boxes, target, mask = output["boxes"], batch["boxes"], batch["inputs"]["room_mask"]
    pairs = pair_mask(mask)
    box = ((boxes - target).square().sum(-1) * mask).sum() / (mask.sum() * 4)
    area = ((boxes[..., 2:].prod(-1) - target[..., 2:].prod(-1)).square() * mask)
    area = area.sum() / mask.sum()
    adjacency = F.binary_cross_entropy_with_logits(
        output["adjacency_logits"][pairs], batch["adjacency"][pairs]
    )
    overlap = (intersections(boxes) * pairs).sum() / pairs.sum().clamp_min(1)
    minimum = (batch["inputs"]["features"][..., 0] - boxes[..., 2:].prod(-1)).clamp_min(0)
    minimum = (minimum.square() * mask).sum() / mask.sum()
    total = box + 0.1 * area + 0.05 * adjacency + 0.1 * overlap + minimum
    return {"loss": total, "box_mse": box, "area_mse": area,
            "adjacency_bce": adjacency, "overlap": overlap, "minimum_penalty": minimum}


def evaluate(model, data, split, batch_size=32):
    """Micro room/pair metrics; geometry pass rates are per complete plan."""
    model.eval()
    sums = {k: 0.0 for k in ("absolute_error", "squared_error", "iou", "tp", "fp", "fn",
                            "plans", "rooms", "loss", "inside", "no_overlap", "minimum", "valid")}
    predictions = []
    with torch.no_grad():
        for batch in data.batches(split, batch_size):
            output = model(batch["inputs"])
            boxes, target, mask = output["boxes"], batch["boxes"], batch["inputs"]["room_mask"]
            if not all(torch.isfinite(t).all() for t in output.values()):
                raise ValueError("Non-finite model output.")
            sums["loss"] += float(loss_terms(output, batch)["loss"]) * len(batch["ids"])
            sums["rooms"] += int(mask.sum())
            sums["plans"] += len(batch["ids"])
            error = boxes - target
            sums["absolute_error"] += float((error.abs().sum(-1) * mask).sum())
            sums["squared_error"] += float((error.square().sum(-1) * mask).sum())
            low = torch.maximum(boxes[..., :2], target[..., :2])
            high = torch.minimum(boxes[..., :2] + boxes[..., 2:],
                                 target[..., :2] + target[..., 2:])
            inter = (high - low).clamp_min(0).prod(-1)
            union = boxes[..., 2:].prod(-1) + target[..., 2:].prod(-1) - inter
            sums["iou"] += float((inter / union.clamp_min(1e-12) * mask).sum())
            pairs = pair_mask(mask)
            predicted = output["adjacency_logits"] >= 0
            actual = batch["adjacency"].bool()
            sums["tp"] += int((predicted & actual & pairs).sum())
            sums["fp"] += int((predicted & ~actual & pairs).sum())
            sums["fn"] += int((~predicted & actual & pairs).sum())
            inside_room = ((boxes[..., :2] >= -1e-6).all(-1)
                           & (boxes[..., :2] + boxes[..., 2:] <= 1 + 1e-6).all(-1)
                           & (boxes[..., 2:] > 0).all(-1))
            inside = (inside_room | ~mask).all(-1)
            # Fixed physical tolerance: at most one square millimetre of overlap.
            area_m2 = batch["inputs"]["footprint_m"].prod(-1)
            overlap = intersections(boxes) * area_m2[:, None, None]
            no_overlap = ~((overlap > 1e-6) & pairs).any(-1).any(-1)
            min_room = (boxes[..., 2:].prod(-1) + 1e-8
                        >= batch["inputs"]["features"][..., 0]) | ~mask
            minimum = min_room.all(-1)
            for key, values in (("inside", inside), ("no_overlap", no_overlap),
                                ("minimum", minimum), ("valid", inside & no_overlap & minimum)):
                sums[key] += int(values.sum())
            for i, sample_id in enumerate(batch["ids"]):
                n = int(mask[i].sum())
                predictions.append({"id": sample_id, "boxes": boxes[i, :n].tolist(),
                                    "geometric_valid": bool((inside & no_overlap & minimum)[i])})
    p, r = sums["plans"], sums["rooms"]
    metrics = {
        "plan_count": int(p), "room_count": int(r), "loss": sums["loss"] / p,
        "box_mae": sums["absolute_error"] / (r * 4),
        "box_mse": sums["squared_error"] / (r * 4), "mean_room_iou": sums["iou"] / r,
        "adjacency_f1": 2 * sums["tp"] / max(2 * sums["tp"] + sums["fp"] + sums["fn"], 1),
        "inside_rate": sums["inside"] / p, "no_overlap_rate": sums["no_overlap"] / p,
        "minimum_area_rate": sums["minimum"] / p, "geometric_valid_rate": sums["valid"] / p,
    }
    return metrics, predictions
