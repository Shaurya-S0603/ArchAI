"""Command-line entrypoint for the ArchAI generator benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from archai.evaluation.benchmark import evaluate_benchmark, report_to_markdown
from archai.evaluation.candidates import CANDIDATE_NAMES, get_candidate
from archai.evaluation.dataset import load_benchmark


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate an ArchAI generator candidate.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/benchmarks/v1"),
        help="Benchmark directory or briefs.jsonl path.",
    )
    parser.add_argument(
        "--candidate",
        choices=CANDIDATE_NAMES,
        default=CANDIDATE_NAMES[0],
        help="Named generator candidate to evaluate.",
    )
    parser.add_argument("--json", type=Path, help="Optional JSON report destination.")
    parser.add_argument("--markdown", type=Path, help="Optional Markdown report destination.")
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Return a non-zero exit code when a regression gate fails.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    manifest, cases = load_benchmark(args.dataset)
    report = evaluate_benchmark(
        cases,
        generator=get_candidate(args.candidate),
        candidate_name=args.candidate,
    )
    report["benchmark"] = {
        "name": manifest["name"],
        "schema_version": manifest["schema_version"],
        "license": manifest["license"],
    }
    markdown = report_to_markdown(report)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(f"{json.dumps(report, indent=2, sort_keys=True)}\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 1 if args.enforce and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
