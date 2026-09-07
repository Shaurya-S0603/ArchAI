"""Evaluate a frozen model plus repair against a matched reference and frozen solver."""

import argparse
import json
import math
import time
from dataclasses import asdict
from pathlib import Path
from statistics import fmean

import torch

from archai.datasets.schema import digest, encode
from archai.evaluation.benchmark import evaluate_benchmark
from archai.evaluation.comparison import compare_reports
from archai.evaluation.dataset import build_synthetic_cases, dataset_digest, load_benchmark
from archai.services.layout_generator import building_bounds_for_brief
from archai_ml.data import encode_programs
from archai_ml.experiment import (
    TypeMeanReference,
    code_identity,
    json_bytes,
    load_run,
    publish_directory,
)
from archai_ml.preview import prediction_sheet
from archai_ml.repair import REPAIR_VERSION, RepairConfig, program_specs, repair_candidates


def normalized_boxes(layout):
    b = layout.building_bounds
    return [[(r.x - b["x"]) / b["width"], (r.y - b["y"]) / b["depth"],
             r.width / b["width"], r.depth / b["depth"]] for r in layout.rooms]


def raw_validity(brief, boxes):
    b = building_bounds_for_brief(brief)
    specs = program_specs(brief)
    inside, minimum, no_overlap = True, True, True
    for i, (spec, (x, y, w, h)) in enumerate(zip(specs, boxes, strict=True)):
        inside &= x >= 0 and y >= 0 and x + w <= 1 + 1e-6 and y + h <= 1 + 1e-6
        minimum &= (w * b["width"] >= 1.8 and h * b["depth"] >= 1.8
                    and w * h * b["width"] * b["depth"] + 1e-6 >= spec.minimum_area)
        for a, c, d, e in boxes[:i]:
            area = max(0, min(x + w, a + d) - max(x, a)) * max(0, min(y + h, c + e) - max(y, c))
            no_overlap &= area * b["width"] * b["depth"] <= 1e-6
    return {"boundary": inside, "minimum_area_and_dimensions": minimum, "no_overlap": no_overlap}


class RepairedCandidate:
    def __init__(self, run: Path, config=RepairConfig(), reference=False):
        config.validate()
        started = time.perf_counter()
        self.model, self.training = load_run(run)
        if reference:
            self.model = TypeMeanReference(json.loads((Path(run) / "reference.json").read_text()))
        self.load_seconds = time.perf_counter() - started
        self.config, self.history, self.examples = config, [], []
        self.name = "repaired-type-reference-v1" if reference else "repaired-neural-v1"

    def __call__(self, brief):
        started = time.perf_counter()
        specs, bounds = program_specs(brief), building_bounds_for_brief(brief)
        program = {"footprint_m": [bounds["width"], bounds["depth"]],
                   "room_types": [s.type for s in specs]}
        with torch.no_grad():
            boxes = self.model(encode_programs([program]))["boxes"][0].tolist()
        proposal = {"room_types": program["room_types"], "boxes": boxes}
        record = {"brief_digest": digest(brief.to_dict()), "raw": raw_validity(brief, boxes)}
        try:
            layouts, diagnostics = repair_candidates(brief, proposal, self.config)
        except ValueError as exc:
            self.history.append({**record, "returned": 0, "error": str(exc),
                                 "seconds": time.perf_counter() - started})
            raise
        self.history.append({**record, **diagnostics, "seconds": time.perf_counter() - started,
                             "displacements": [l.metrics["repair"]["coordinate_mae_displacement"]
                                               for l in layouts],
                             "strict_validated": all(all(l.metrics["repair"]["gates"].values())
                                                     for l in layouts)})
        if len(self.examples) < 6:
            self.examples.append({"id": f"case-{len(self.examples) + 1}",
                                  "footprint_m": program["footprint_m"],
                                  "room_types": program["room_types"], "raw": boxes,
                                  "repaired": normalized_boxes(layouts[0])})
        return layouts


def summarize_history(candidate):
    history = candidate.history
    elapsed = sorted(r["seconds"] for r in history)
    shifts = [d for r in history for d in r.get("displacements", [])]
    count = len(history)
    return {"cases": count, "returned_layouts": sum(r["returned"] for r in history),
            "failed_cases": sum(r["returned"] == 0 for r in history),
            "strict_validated_rate": fmean(r.get("strict_validated", False) for r in history),
            "raw_geometry_valid_rate": fmean(all(r["raw"].values()) for r in history),
            "raw_no_overlap_rate": fmean(r["raw"]["no_overlap"] for r in history),
            "four_distinct_rate": fmean(r["returned"] >= 4 for r in history),
            "five_distinct_rate": fmean(r["returned"] == 5 for r in history),
            "failed_solver_attempts": sum(len(r.get("failures", [])) for r in history),
            "mean_coordinate_displacement": fmean(shifts) if shifts else None,
            "cpu_seconds_p50": elapsed[math.ceil(count * .5) - 1],
            "cpu_seconds_p95": elapsed[math.ceil(count * .95) - 1],
            "cpu_seconds_max": elapsed[-1], "checkpoint_load_seconds": candidate.load_seconds}


def stress(candidate, count):
    if type(count) is not int or not 1 <= count <= 10000:
        raise ValueError("Stress count must be between 1 and 10000.")
    candidate.history.clear()
    cases = build_synthetic_cases(count=count, seed=20260907)
    for case in cases:
        try:
            candidate(case.brief)
        except ValueError:
            pass  # Expected rejection is recorded; programming/runtime exceptions still fail the run.
    return {"seed": 20260907, "briefs_digest": dataset_digest(cases),
            **summarize_history(candidate)}


def run_comparison(run, output, config, benchmark=Path("data/benchmarks/v1"), limit=None,
                   stress_count=0, frozen=Path("reports/phase2d-baseline.json")):
    if Path(output).exists():
        raise ValueError("Output already exists; choose a new comparison directory.")
    _, cases = load_benchmark(benchmark)
    if limit is not None:
        if type(limit) is not int or not 1 <= limit <= len(cases):
            raise ValueError("Invalid benchmark limit.")
        cases = cases[:limit]
    candidate = RepairedCandidate(run, config)
    expected = json.loads(Path(frozen).read_text())["training"]
    if (candidate.training["state_digest"] != expected["state_digest"]
            or candidate.training["dataset_digest"] != expected["dataset_digest"]):
        raise ValueError("Repair comparison requires the frozen Phase 2D model and data.")
    reference = RepairedCandidate(run, config, reference=True)
    baseline = evaluate_benchmark(cases)
    neural = evaluate_benchmark(cases, candidate, candidate.name)
    prior = evaluate_benchmark(cases, reference, reference.name)
    comparison = compare_reports(baseline, neural)
    neural_diagnostics, reference_diagnostics = summarize_history(candidate), summarize_history(reference)
    solver = json.loads(Path("reports/phase2c-solver-comparison.json").read_text())
    solver_comparable = solver["dataset_sha256"] == neural["dataset_sha256"]
    summary = neural["summary"]
    component_gates = {
        "every_brief_returns_valid_repair": summary["case_success_rate"] == 1,
        "strict_geometry_and_topology": neural_diagnostics["strict_validated_rate"] == 1,
        "room_program": summary["program_match_rate"] == 1,
    }
    generator_gates = {
        "existing_comparison": comparison["passed"],
        "adjacency_gain_ten_percentage_points": comparison["deltas"]["mean_adjacency_satisfaction"] >= .1,
        "four_distinct_concepts": neural_diagnostics["four_distinct_rate"] == 1,
        "five_concept_contract": summary["concept_count_pass_rate"] == 1,
        "observed_cpu_p95_under_five_seconds": neural_diagnostics["cpu_seconds_p95"] < 5,
    }
    files = {"neural.json": json_bytes(neural), "reference.json": json_bytes(prior),
             "baseline.json": json_bytes(baseline), "neural-cases.json": json_bytes(candidate.history),
             "reference-cases.json": json_bytes(reference.history),
             "examples.json": json_bytes(candidate.examples)}
    rows = [{"id": e["id"], "footprint_m": e["footprint_m"],
             "rooms": [{"type": t, "box": b} for t, b in zip(e["room_types"], e["raw"], strict=True)]}
            for e in candidate.examples]
    predictions = [{"id": e["id"], "boxes": e["repaired"], "geometric_valid": True}
                   for e in candidate.examples]
    files["preview.png"] = prediction_sheet(
        rows, predictions, title="ArchAI Phase 2E | Raw neural (left) / validated repair (right)",
        subtitle="First six benchmark briefs, first selected repair. Restricted corridor/slot projection.",
    )
    stress_result = stress(candidate, stress_count) if stress_count else None
    report = {"repair_version": REPAIR_VERSION, "config": asdict(config),
              "model_state_digest": candidate.training["state_digest"],
              "training_dataset_digest": candidate.training["dataset_digest"],
              "benchmark_digest": neural["dataset_sha256"], "environment": code_identity(),
              "baseline": baseline["summary"], "neural": summary, "reference": prior["summary"],
              "frozen_solver": solver["candidate"]["summary"] if solver_comparable else None,
              "solver_source": "reports/phase2c-solver-comparison.json",
              "neural_diagnostics": neural_diagnostics, "reference_diagnostics": reference_diagnostics,
              "neural_vs_reference_adjacency_delta": round(summary["mean_adjacency_satisfaction"]
                  - prior["summary"]["mean_adjacency_satisfaction"], 4),
              "component_gates": component_gates, "component_passed": all(component_gates.values()),
              "generator_gates": generator_gates, "stress": stress_result, "production_ready": False,
              "remaining_release_requirements": ["independent licensed real-plan validation",
                                                 "blinded human preference above 60 percent",
                                                 "production API integration and fallback validation"]}
    if not stress_result or stress_result["cases"] < 1000 or stress_result["failed_cases"]:
        report["remaining_release_requirements"].append("1000-brief complete-generator stress gate")
    files["report.json"] = json_bytes(report)
    publish_directory(Path(output), files, {"repair_version": REPAIR_VERSION,
                                           "model_state_digest": report["model_state_digest"]})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--benchmark", default=Path("data/benchmarks/v1"), type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--stress-count", type=int, default=0)
    parser.add_argument("--frozen", default=Path("reports/phase2d-baseline.json"), type=Path)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = RepairConfig(**json.loads(args.config.read_text()))
        report = run_comparison(args.run, args.output, config, args.benchmark, args.limit,
                                args.stress_count, args.frozen)
        print(encode(report))
        return int(args.enforce and not report["component_passed"])
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        parser.exit(2, f"ArchAI repair: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
