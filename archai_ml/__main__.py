"""Optional research CLI: train, explicitly evaluate a split, or predict a program."""

import argparse
import json
from pathlib import Path

import torch

from archai.datasets.schema import encode
from archai_ml.data import encode_programs
from archai_ml.experiment import TrainConfig, evaluate_run, load_run, train


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    training = commands.add_parser("train")
    training.add_argument("--dataset", type=Path, required=True)
    training.add_argument("--output", type=Path, required=True)
    training.add_argument("--config", type=Path, required=True)
    training.add_argument("--enforce", action="store_true")
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--dataset", type=Path, required=True)
    evaluation.add_argument("--run", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--split", choices=("train", "validation", "test"), required=True)
    prediction = commands.add_parser("predict")
    prediction.add_argument("--run", type=Path, required=True)
    prediction.add_argument("--program", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "train":
            config = TrainConfig(**json.loads(args.config.read_text()))
            report = train(args.dataset, args.output, config, progress=True)
            print(encode(report))
            return int(args.enforce and not report["research_gate_passed"])
        if args.command == "evaluate":
            print(encode(evaluate_run(args.dataset, args.run, args.output, args.split)))
        else:
            program = json.loads(args.program.read_text())
            model, _ = load_run(args.run)
            with torch.no_grad():
                output = model(encode_programs([program]))
            adjacency = output["adjacency_logits"][0].sigmoid()
            adjacency.fill_diagonal_(0)
            print(encode({"room_types": program["room_types"], "footprint_m": program["footprint_m"],
                          "normalized_boxes": output["boxes"][0].tolist(),
                          "adjacency_probabilities": adjacency.tolist(),
                          "status": "raw research prediction; constraint repair required"}))
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        parser.exit(2, f"ArchAI ML: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
