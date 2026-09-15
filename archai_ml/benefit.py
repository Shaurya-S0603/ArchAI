"""Phase 2G validation-only ablation; a good raw predictor is not a release gate.

Each arm gets five proposals, ten solver attempts, the same deterministic work
budget, the same strict validator and the same bounded diversity search. The
solver-only arm removes the proposal term and receives no learned information.
"""

import argparse
import json
import math
import time
from dataclasses import asdict
from pathlib import Path
from random import Random
from statistics import fmean

import torch

from archai.datasets.conditioning import (
    VERSION,
    prepare_conditioning_data,
    read_protocol,
)
from archai.datasets.schema import digest, geometry_key
from archai.evaluation.benchmark import adjacency_satisfaction_score, evaluate_benchmark
from archai.evaluation.dataset import BenchmarkCase
from archai.models import DesignBrief
from archai.services.cost_estimator import COST_MODEL_VERSION
from archai.services.layout_generator import building_bounds_for_brief, generate_layouts
from archai_ml.conditioning import (
    ConceptTypeReference,
    ConditioningData,
    load_conditioned_run,
    train_conditioned,
)
from archai_ml.data import encode_programs
from archai_ml.diversity import (
    MAXIMUM_SEARCH_NODES,
    reflow_variants,
    select_distinct,
    validate_concepts,
)
from archai_ml.experiment import TrainConfig, code_identity, json_bytes, publish_directory
from archai_ml.repair import (
    RepairConfig,
    _canonical,
    program_specs,
    project_layout,
    validate_proposal,
)
from archai_ml.repair_evaluation import raw_validity


def repair_proposals(brief, proposals, config, *, solver_only=False):
    config.validate()
    if not isinstance(proposals, list) or len(proposals) != 5:
        raise ValueError("The matched repair requires five proposals.")
    for proposal in proposals:
        validate_proposal(brief, proposal)
    templates = sorted(generate_layouts(brief), key=lambda l: l.id)
    pool, seen, failures = [], set(), []
    for repeat in range(config.passes):
        for index, (template, proposal) in enumerate(zip(templates, proposals, strict=True)):
            try:
                layout = project_layout(brief, proposal, template, (index + repeat) % 5, config,
                                        proposal_weight=0 if solver_only else 1)
            except ValueError as exc:
                failures.append(str(exc))
                continue
            key = geometry_key(_canonical(layout), 3)
            if key not in seen:
                seen.add(key)
                layout.metrics["repair"]["concept_id"] = index
                pool.append(layout)

    def order(layout):
        return (-adjacency_satisfaction_score(layout, brief),
                0 if solver_only else layout.metrics["repair"]["coordinate_mae_displacement"],
                geometry_key(_canonical(layout), 3))

    pool.sort(key=order)
    selected, nodes = select_distinct(pool, config.minimum_separation)
    expanded = 0
    for parent in list(pool):
        if len(selected) == 5 or nodes >= MAXIMUM_SEARCH_NODES:
            break
        concept = parent.metrics["repair"]["concept_id"]
        for layout in reflow_variants(brief, proposals[concept], parent):
            key = geometry_key(_canonical(layout), 3)
            if key not in seen:
                seen.add(key)
                layout.metrics["repair"]["concept_id"] = concept
                pool.append(layout)
                expanded += 1
        pool.sort(key=order)
        selected, used = select_distinct(pool, config.minimum_separation,
                                          MAXIMUM_SEARCH_NODES - nodes)
        nodes += used
    for index, layout in enumerate(selected):
        layout.id = f"archai-conditioning-{index + 1}"
        layout.name = f"Conditioning experiment concept {index + 1}"
    # Even a shortfall must remain inspectable; callers never pad it with copies.
    return selected, {"attempts": 5 * config.passes, "failures": failures,
                      "expanded": expanded, "selection_nodes": nodes}


class MatchedCandidate:
    def __init__(self, model, config, *, solver_only=False):
        self.model, self.config, self.solver_only, self.history = model, config, solver_only, []

    def __call__(self, brief):
        started = time.perf_counter()
        bounds, types = building_bounds_for_brief(brief), [s.type for s in program_specs(brief)]
        program = {"footprint_m": [bounds["width"], bounds["depth"]], "room_types": types}
        if self.solver_only:
            boxes = [[[.25, .25, .5, .5] for _ in types] for _ in range(5)]
        else:
            inputs = encode_programs([program] * 5)
            inputs["concept_ids"] = torch.arange(5)
            with torch.no_grad():
                predicted = self.model(inputs)["boxes"]
            if not torch.isfinite(predicted).all():
                raise RuntimeError("Non-finite conditioned proposal.")
            boxes = predicted.tolist()
        proposals = [{"room_types": types, "boxes": b} for b in boxes]
        raw = [raw_validity(brief, b) for b in boxes]
        layouts, diagnostics = repair_proposals(brief, proposals, self.config,
                                                 solver_only=self.solver_only)
        error = None
        try:
            validate_concepts(layouts, brief, self.config.minimum_separation)
        except ValueError as exc:
            error = str(exc)
        record = {"brief_digest": digest(brief.to_dict()), **diagnostics,
                  "seconds": time.perf_counter() - started, "returned": len(layouts),
                  "five_strict_distinct": error is None, "error": error,
                  "raw_no_overlap_rate": fmean(r["no_overlap"] for r in raw),
                  "raw_valid_rate": fmean(all(r.values()) for r in raw),
                  "mean_displacement": (fmean(l.metrics["repair"]["coordinate_mae_displacement"]
                                               for l in layouts) if layouts else None)}
        self.history.append(record)
        if error:
            raise ValueError(error)
        return layouts


def summarize(candidate):
    history = candidate.history
    if not history:
        raise ValueError("No candidate evidence recorded.")
    times = sorted(r["seconds"] for r in history)
    shifts = [r["mean_displacement"] for r in history if r["mean_displacement"] is not None]
    return {"cases": len(history), "five_strict_distinct_rate": fmean(
                r["five_strict_distinct"] for r in history),
            "raw_no_overlap_rate": fmean(r["raw_no_overlap_rate"] for r in history),
            "raw_valid_rate": fmean(r["raw_valid_rate"] for r in history),
            "mean_displacement": fmean(shifts) if shifts and not candidate.solver_only else None,
            "failed_solver_attempts": sum(len(r["failures"]) for r in history),
            "solver_attempts": sum(r["attempts"] for r in history),
            "warm_seconds_p95": times[math.ceil(.95 * len(times)) - 1]}


def paired_adjacency(first, second, samples=2000, seed=20260912):
    if (first["dataset_sha256"] != second["dataset_sha256"]
            or first["cost_model_version"] != second["cost_model_version"]
            or [c["case_id"] for c in first["cases"]] != [c["case_id"] for c in second["cases"]]
            or not first["cases"] or type(samples) is not int or samples < 100):
        raise ValueError("Paired comparison requires identical nonempty cohorts and cost semantics.")
    deltas = [a["mean_adjacency_satisfaction"] - b["mean_adjacency_satisfaction"]
              for a, b in zip(first["cases"], second["cases"], strict=True)]
    rng = Random(seed)
    boot = sorted(fmean(rng.choices(deltas, k=len(deltas))) for _ in range(samples))
    return {"briefs": len(deltas), "mean_delta": fmean(deltas),
            "percentile_95_interval": [boot[int(.025 * samples)], boot[int(.975 * samples) - 1]],
            "wins": sum(d > 0 for d in deltas), "ties": sum(d == 0 for d in deltas),
            "losses": sum(d < 0 for d in deltas), "resampling_unit": "brief",
            "scope": "validation exploratory interval, conditional on this training seed"}


def run_benefit(data_directory, conditioned_run, unconditioned_run, output):
    if Path(output).exists():
        raise ValueError("Benefit output already exists.")
    data = ConditioningData(data_directory)
    protocol = data.context["protocol"]
    if protocol != read_protocol() or protocol["cost_model_version"] != COST_MODEL_VERSION:
        raise ValueError("Benefit evaluation requires the frozen Phase 2G protocol.")
    conditioned, c_report = load_conditioned_run(conditioned_run, data.identity)
    unconditioned, u_report = load_conditioned_run(unconditioned_run, data.identity)
    if (not c_report["conditioned"] or u_report["conditioned"]
            or c_report["config"] != u_report["config"]
            or c_report["parameters"] != u_report["parameters"]
            or {k: v for k, v in c_report["config"].items() if k != "seed"} != protocol["training"]
            or c_report["config"]["seed"] not in protocol["training_seeds"]):
        raise ValueError("The paired arms must have identical predeclared training budgets.")
    cases = [BenchmarkCase(c["id"], "validation", DesignBrief.from_dict(c["brief"]))
             for c in data.context["cohorts"]["validation"]["cases"]]
    repair = RepairConfig(**protocol["repair"])
    models = {"conditioned": conditioned, "unconditioned": unconditioned,
              "concept_type_reference": ConceptTypeReference(ConceptTypeReference.fit(data)),
              "solver_only": None}
    results, files = {}, {}
    for name, model in models.items():
        candidate = MatchedCandidate(model, repair, solver_only=name == "solver_only")
        benchmark = evaluate_benchmark(cases, candidate, name)
        results[name] = {"benchmark": benchmark["summary"], "diagnostics": summarize(candidate)}
        files[f"{name}-benchmark.json"] = json_bytes(benchmark)
        files[f"{name}-cases.json"] = json_bytes(candidate.history)
        print(json.dumps({"arm": name, **results[name]}), flush=True)
    comparisons = {name: paired_adjacency(json.loads(files["conditioned-benchmark.json"]),
                                         json.loads(files[f"{name}-benchmark.json"]),
                                         protocol["bootstrap_samples"], protocol["bootstrap_seed"])
                   for name in models if name != "conditioned"}
    raw_gain = 1 - c_report["validation"]["box_mae"] / u_report["validation"]["box_mae"]
    engineering = {
        "both_models_learn": c_report["learning_passed"] and u_report["learning_passed"],
        "complete_case_accounting": all(v["diagnostics"]["cases"] == len(cases)
                                         for v in results.values()),
        "equal_solver_attempt_budgets": all(v["diagnostics"]["solver_attempts"]
                                              == len(cases) * 5 * repair.passes
                                              for v in results.values()),
        "all_arms_five_strict_distinct": all(v["diagnostics"]["five_strict_distinct_rate"] == 1
                                             for v in results.values()),
    }
    neural_gates = {
        "raw_mae_improves_ten_percent": raw_gain >= protocol["raw_mae_relative_improvement"],
        "positive_adjacency_interval_vs_all_controls": all(
            c["percentile_95_interval"][0] > 0 for c in comparisons.values()),
        "no_budget_or_diversity_regression": all(
            results["conditioned"]["benchmark"][metric] + 1e-9 >= v["benchmark"][metric]
            for name, v in results.items() if name != "conditioned"
            for metric in ("budget_fit_rate", "mean_diversity_score")),
        "observed_warm_p95_under_five_seconds": results["conditioned"]["diagnostics"][
            "warm_seconds_p95"] < protocol["warm_cpu_p95_limit_seconds"],
        "all_arms_five_strict_distinct": engineering["all_arms_five_strict_distinct"],
    }
    report = {"version": VERSION, "stage": "validation", "seed": c_report["config"]["seed"],
              "environment": code_identity(), "data_identity": data.identity,
              "protocol_digest": digest(protocol), "repair_budget": asdict(repair),
              "total_deterministic_work_limit_per_brief": repair.deterministic_limit * 5 * repair.passes,
              "raw_validation": {"conditioned": c_report["validation"],
                                 "unconditioned": u_report["validation"],
                                 "concept_type_reference": c_report["reference"]},
              "state_digests": {"conditioned": c_report["state_digest"],
                                "unconditioned": u_report["state_digest"]},
              "raw_mae_relative_improvement": raw_gain, "results": results,
              "paired_adjacency": comparisons, "engineering_gates": engineering,
              "engineering_passed": all(engineering.values()), "neural_gates": neural_gates,
              "validation_neural_benefit": all(neural_gates.values()),
              "test_evaluated": False, "qualified_model_release": False,
              "remaining_requirements": ["confirmation on a newly locked holdout after selection",
                                         "independent licensed real-plan evaluation",
                                         "blinded human preference above 60 percent"]}
    files["report.json"] = json_bytes(report)
    publish_directory(Path(output), files, {"version": VERSION, "data_identity": data.identity})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    pair = sub.add_parser("train-pair")
    pair.add_argument("--data", type=Path, required=True)
    pair.add_argument("--output", type=Path, required=True)
    pair.add_argument("--seed", type=int, required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--data", type=Path, required=True)
    compare.add_argument("--runs", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    compare.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare_conditioning_data(args.output)
    elif args.command == "train-pair":
        protocol = read_protocol()
        data = ConditioningData(args.data)
        if data.context["protocol"] != protocol or args.seed not in protocol["training_seeds"]:
            raise ValueError("Training requires the frozen data protocol and a declared seed.")
        if args.output.exists():
            raise ValueError("Paired run output already exists.")
        config = TrainConfig(seed=args.seed, **protocol["training"])
        result = {name: train_conditioned(args.data, args.output / name, config, flag, progress=True)
                  for name, flag in (("conditioned", True), ("unconditioned", False))}
    else:
        result = run_benefit(args.data, args.runs / "conditioned", args.runs / "unconditioned",
                             args.output)
        print(json.dumps(result), flush=True)
        return int(args.enforce and not result["engineering_passed"])
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
