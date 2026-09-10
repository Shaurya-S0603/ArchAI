"""python -m archai.datasets {pilot,ingest,validate}."""

import argparse
import json
from pathlib import Path

from archai.datasets.pilot import build_pilot, evaluation_exclusions
from archai.datasets.pipeline import load_dataset, preprocess, write_dataset
from archai.datasets.schema import encode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pilot = commands.add_parser("pilot", help="Build the fresh, MIT synthetic pilot")
    pilot.add_argument("--output", type=Path, required=True)
    pilot.add_argument("--count", type=int, default=120)
    pilot.add_argument("--seed", type=int, default=20260905)
    ingest = commands.add_parser("ingest", help="Preprocess an already-reviewed rectangle source")
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--source", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    ingest.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/v1"))
    ingest.add_argument("--seed", type=int, default=20260905)
    validate = commands.add_parser("validate", help="Verify artifact checksums and split integrity")
    validate.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "pilot":
            result = build_pilot(args.output, args.count, args.seed)
        elif args.command == "ingest":
            _, keys = evaluation_exclusions(args.benchmark)
            source = json.loads(args.source.read_text())
            rows, result = preprocess(args.input.read_bytes(), source, args.seed, keys)
            write_dataset(args.output, rows, result, source, args.seed)
        else:
            result, _ = load_dataset(args.directory)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Dataset error: {exc}\n")
    print(encode(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
