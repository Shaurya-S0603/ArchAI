"""Stateless CPU proposal/repair wrapper for the explicitly experimental API engine."""

from pathlib import Path
from threading import Lock

import torch

from archai.services.layout_generator import building_bounds_for_brief
from archai_ml.data import encode_programs
from archai_ml.diversity import diverse_candidates, validate_concepts
from archai_ml.experiment import load_run
from archai_ml.repair import program_specs

# Only the frozen, evaluated synthetic checkpoint is eligible for this preview.
FROZEN_STATE = "344a53149ef17be0a3b21e5284c4df742c27c59852629cbfbbc788d7a543f3c1"
FROZEN_DATA = "e0efc4064fec21e0ca430ae356705052ba6002c70908fc3470606ddc944fd9aa"


class NeuralEngine:
    def __init__(self, run):
        if not run:
            raise ValueError("Experimental engine requires a checkpoint directory.")
        self.model, self.training = load_run(Path(run), FROZEN_DATA)
        if self.training["state_digest"] != FROZEN_STATE:
            raise ValueError("Experimental engine requires the evaluated frozen checkpoint.")
        self.lock = Lock()

    def __call__(self, brief):
        bounds = building_bounds_for_brief(brief)
        types = [s.type for s in program_specs(brief)]
        program = {"footprint_m": [bounds["width"], bounds["depth"]], "room_types": types}
        # no_grad is thread-local; set it in the worker executing inference.
        with self.lock, torch.no_grad():
            boxes = self.model(encode_programs([program]))["boxes"][0].tolist()
            layouts, _ = diverse_candidates(brief, {"room_types": types, "boxes": boxes})
        validate_concepts(layouts, brief)
        return layouts
