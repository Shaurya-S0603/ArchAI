"""Small dense message-passing regressor with bounded boxes and symmetric edges."""

import torch
from torch import nn

from archai.datasets.schema import ROOM_TYPES
from archai_ml.data import FEATURE_COUNT


class RoomGraphModel(nn.Module):
    def __init__(self, hidden_size: int = 64, layers: int = 4):
        super().__init__()
        self.embedding = nn.Embedding(len(ROOM_TYPES) + 1, 16, padding_idx=0)
        self.input = nn.Linear(16 + FEATURE_COUNT, hidden_size)
        self.messages = nn.ModuleList(nn.Linear(hidden_size * 3, hidden_size)
                                      for _ in range(layers))
        self.norms = nn.ModuleList(nn.LayerNorm(hidden_size) for _ in range(layers))
        self.box_head = nn.Linear(hidden_size, 4)
        self.edge_head = nn.Sequential(nn.Linear(hidden_size * 2, hidden_size), nn.SiLU(),
                                       nn.Linear(hidden_size, 1))

    def forward(self, inputs: dict) -> dict:
        mask = inputs["room_mask"]
        m = mask.unsqueeze(-1)
        pair = mask.unsqueeze(1) & mask.unsqueeze(2)
        graph = inputs["desired_graph"] * pair
        graph = graph / graph.sum(-1, keepdim=True).clamp_min(1)
        h = torch.nn.functional.silu(self.input(torch.cat([
            self.embedding(inputs["type_ids"]), inputs["features"]
        ], dim=-1))) * m
        for layer, norm in zip(self.messages, self.norms, strict=True):
            global_h = h.sum(1, keepdim=True) / m.sum(1, keepdim=True).clamp_min(1)
            neighbors = torch.bmm(graph, h)
            update = layer(torch.cat([h, neighbors, global_h.expand_as(h)], dim=-1))
            h = norm(h + torch.nn.functional.silu(update)) * m
        raw = torch.sigmoid(self.box_head(h))
        size = raw[..., 2:]
        boxes = torch.cat([raw[..., :2] * (1 - size), size], dim=-1) * m
        a, b = h.unsqueeze(2), h.unsqueeze(1)
        logits = self.edge_head(torch.cat([a + b, torch.abs(a - b)], dim=-1)).squeeze(-1)
        pair = pair & ~torch.eye(mask.shape[1], dtype=torch.bool, device=mask.device)
        return {"boxes": boxes, "adjacency_logits": logits.masked_fill(~pair, 0)}
