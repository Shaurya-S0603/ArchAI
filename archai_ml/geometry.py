"""Prospective Phase 2H geometry objective, isolated from frozen serving/training."""

import argparse
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path

import torch

from archai.datasets.schema import ROOM_TYPES, digest
from archai.evaluation.benchmark import evaluate_benchmark
from archai.evaluation.dataset import BenchmarkCase
from archai.models import DesignBrief
from archai.services.cost_estimator import COST_MODEL_VERSION
from archai_ml.benefit import MatchedCandidate, paired_adjacency, summarize
from archai_ml.conditioning import ConceptGraphModel, ConceptTypeReference, ConditioningData
from archai_ml.experiment import (
    TrainConfig,
    code_identity,
    deterministic_cpu,
    json_bytes,
    publish_directory,
    state_digest,
)
from archai_ml.objective import evaluate, intersections, loss_terms, pair_mask
from archai_ml.repair import RepairConfig

VERSION = "geometry-tail-v1"
CONFIG = Path(__file__).resolve().parents[1] / "ml/configs/phase2h-v1.json"


def read_protocol():
    protocol = json.loads(CONFIG.read_text())
    if (protocol["version"] != VERSION
            or protocol["checkpoint_selection"] != "unchanged_base_validation_loss"
            or protocol["cost_model_version"] != COST_MODEL_VERSION):
        raise ValueError("Unsupported geometry protocol.")
    return protocol


class DevelopmentData(ConditioningData):
    """Admission verifies the complete dataset; only train/validation can be selected."""

    def select(self, split):
        if split not in ("train", "validation"):
            raise ValueError("The geometry experiment cannot select the reserved holdout.")
        return super().select(split)


def checked_data(directory, protocol):
    data = DevelopmentData(directory)
    if (digest(data.context["protocol"]) != protocol["data_protocol_digest"]
            or data.manifest["records_digest"] != protocol["records_digest"]
            or data.context["protocol"]["repair"] != protocol["repair"]):
        raise ValueError("Geometry data or repair identity does not match the protocol.")
    return data


def worst_overlap(boxes, mask):
    """One maximum normalized intersection per plan, excluding padding and self pairs."""
    overlaps = intersections(boxes).masked_fill(~pair_mask(mask), 0)
    return overlaps.flatten(1).amax(1)


def geometry_metrics(model, data, batch_size):
    model.eval()
    rows = []
    with torch.no_grad():
        for batch in data.batches("validation", batch_size):
            boxes = model(batch["inputs"])["boxes"]
            if not torch.isfinite(boxes).all():
                raise ValueError("Non-finite geometry output.")
            worst = worst_overlap(boxes, batch["inputs"]["room_mask"])
            areas = batch["inputs"]["footprint_m"].prod(-1)
            for i, sample_id in enumerate(batch["ids"]):
                rows.append({"id": sample_id, "worst_overlap_fraction": float(worst[i]),
                             "worst_overlap_m2": float(worst[i] * areas[i])})
    return {"plans": len(rows), "mean_worst_overlap_fraction": sum(
        r["worst_overlap_fraction"] for r in rows) / len(rows),
        "mean_worst_overlap_m2": sum(r["worst_overlap_m2"] for r in rows) / len(rows)}, rows


def train_run(data_directory, output, config, arm, protocol):
    config.validate()
    if (arm not in ("base", "geometry") or config.seed not in protocol["training_seeds"]
            or {k: v for k, v in asdict(config).items() if k != "seed"} != protocol["training"]):
        raise ValueError("Geometry training requires a declared arm, seed and budget.")
    if Path(output).exists():
        raise ValueError("Geometry training output already exists.")
    data = checked_data(data_directory, protocol)
    deterministic_cpu(config.seed)
    model = ConceptGraphModel(config.hidden_size, config.layers, True)
    initial_state = state_digest(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    initial, _ = evaluate(model, data, "validation", config.batch_size)
    best, best_epoch = initial, 0
    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    history = []
    for epoch in range(1, config.epochs + 1):
        model.train()
        total, count = 0.0, 0
        for batch in data.batches("train", config.batch_size, seed=config.seed + epoch):
            optimizer.zero_grad(set_to_none=True)
            output_boxes = model(batch["inputs"])
            loss = loss_terms(output_boxes, batch)["loss"]
            if arm == "geometry":
                loss = loss + protocol["worst_overlap_weight"] * worst_overlap(
                    output_boxes["boxes"], batch["inputs"]["room_mask"]).mean()
            if not torch.isfinite(loss):
                raise ValueError("Non-finite geometry loss; no checkpoint published.")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            total += float(loss.detach()) * len(batch["ids"])
            count += len(batch["ids"])
        validation, _ = evaluate(model, data, "validation", config.batch_size)
        history.append({"epoch": epoch, "train_loss": total / count, "validation": validation})
        if validation["loss"] < best["loss"]:
            best, best_epoch = validation, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        if epoch == 1 or epoch % 20 == 0:
            print(json.dumps({"arm": arm, "seed": config.seed, "epoch": epoch,
                              "validation_loss": validation["loss"], "best_epoch": best_epoch}),
                  flush=True)
    model.load_state_dict(best_state)
    validation, predictions = evaluate(model, data, "validation", config.batch_size)
    geometry, geometry_rows = geometry_metrics(model, data, config.batch_size)
    report = {"version": VERSION, "arm": arm, "config": asdict(config),
              "protocol_digest": digest(protocol), "data_identity": data.identity,
              "environment": code_identity(), "parameters": sum(p.numel() for p in model.parameters()),
              "initial_state_digest": initial_state, "initial_validation": initial,
              "best_epoch": best_epoch, "validation": validation, "geometry": geometry,
              "state_digest": state_digest(model), "learning_passed": best["loss"] < initial["loss"],
              "training_plans": len(data.select("train")),
              "validation_plans": len(data.select("validation")),
              "test_evaluated": False, "production_ready": False}
    weights = io.BytesIO()
    torch.save(model.state_dict(), weights)
    publish_directory(Path(output), {"weights.pt": weights.getvalue(),
                      "training.json": json_bytes(report), "history.json": json_bytes(history),
                      "validation-predictions.json": json_bytes(predictions),
                      "geometry-cases.json": json_bytes(geometry_rows)},
                      {"version": VERSION, "taxonomy": list(ROOM_TYPES),
                       "data_identity": data.identity, "protocol_digest": digest(protocol)})
    return report


def load_run(directory, data_identity, protocol_digest):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if (manifest.get("version") != VERSION or manifest.get("taxonomy") != list(ROOM_TYPES)
            or manifest.get("data_identity") != data_identity
            or manifest.get("protocol_digest") != protocol_digest):
        raise ValueError("Geometry checkpoint version/data/protocol mismatch.")
    expected = {"weights.pt", "training.json", "history.json", "validation-predictions.json",
                "geometry-cases.json"}
    if set(manifest.get("files", {})) != expected:
        raise ValueError("Invalid geometry checkpoint manifest.")
    for name, checksum in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("Geometry checkpoint checksum mismatch.")
    report = json.loads((directory / "training.json").read_text())
    if (report.get("version") != VERSION or report.get("data_identity") != data_identity
            or report.get("protocol_digest") != protocol_digest
            or report.get("arm") not in ("base", "geometry") or report.get("test_evaluated") is not False):
        raise ValueError("Geometry checkpoint metadata mismatch.")
    config = TrainConfig(**report["config"])
    config.validate()
    deterministic_cpu(config.seed)
    model = ConceptGraphModel(config.hidden_size, config.layers, True)
    model.load_state_dict(torch.load(directory / "weights.pt", map_location="cpu", weights_only=True))
    if (not all(torch.isfinite(t).all() for t in model.state_dict().values())
            or state_digest(model) != report["state_digest"]):
        raise ValueError("Geometry checkpoint tensor integrity failure.")
    return model.eval(), report


def compare(data_directory, runs, output, protocol):
    if Path(output).exists():
        raise ValueError("Geometry comparison output already exists.")
    data = checked_data(data_directory, protocol)
    loaded = {arm: load_run(Path(runs) / arm, data.identity, digest(protocol))
              for arm in ("base", "geometry")}
    base, geo = (loaded[a][1] for a in ("base", "geometry"))
    if (base["arm"] != "base" or geo["arm"] != "geometry" or base["config"] != geo["config"]
            or base["initial_state_digest"] != geo["initial_state_digest"]
            or base["parameters"] != geo["parameters"]
            or base["environment"]["python_source_digest"] != geo["environment"]["python_source_digest"]
            or base["config"]["seed"] not in protocol["training_seeds"]
            or {k: v for k, v in base["config"].items() if k != "seed"} != protocol["training"]):
        raise ValueError("The geometry pair must share declared initial state, source and budget.")
    cases = [BenchmarkCase(c["id"], "validation", DesignBrief.from_dict(c["brief"]))
             for c in data.context["cohorts"]["validation"]["cases"]]
    models = {"geometry": loaded["geometry"][0], "base": loaded["base"][0],
              "concept_type_reference": ConceptTypeReference(ConceptTypeReference.fit(data)),
              "solver_only": None}
    results, files, benchmarks = {}, {}, {}
    repair = RepairConfig(**protocol["repair"])
    for name, model in models.items():
        candidate = MatchedCandidate(model, repair, solver_only=name == "solver_only")
        benchmark = evaluate_benchmark(cases, candidate, name)
        benchmarks[name] = benchmark
        results[name] = {"benchmark": benchmark["summary"], "diagnostics": summarize(candidate)}
        files[f"{name}-benchmark.json"] = json_bytes(benchmark)
        files[f"{name}-cases.json"] = json_bytes(candidate.history)
        print(json.dumps({"arm": name, "seed": geo["config"]["seed"],
                          "five_strict_distinct": results[name]["diagnostics"][
                              "five_strict_distinct_rate"]}), flush=True)
    comparisons = {name: paired_adjacency(benchmarks["geometry"], benchmarks[name],
                    protocol["bootstrap_samples"], protocol["bootstrap_seed"])
                   for name in models if name != "geometry"}
    baseline_overlap = base["geometry"]["mean_worst_overlap_fraction"]
    overlap_gain = (1 - geo["geometry"]["mean_worst_overlap_fraction"] / baseline_overlap
                    if baseline_overlap > 0 else 0.0)
    mae_regression = geo["validation"]["box_mae"] / base["validation"]["box_mae"] - 1
    engineering = {
        "both_models_learn": base["learning_passed"] and geo["learning_passed"],
        "complete_case_accounting": all(v["diagnostics"]["cases"] == len(cases)
                                         for v in results.values()),
        "equal_solver_attempt_budgets": all(v["diagnostics"]["solver_attempts"]
                                             == len(cases) * 5 * repair.passes
                                             for v in results.values()),
        "all_arms_five_strict_distinct": all(v["diagnostics"]["five_strict_distinct_rate"] == 1
                                             for v in results.values()),
    }
    research = {
        "worst_overlap_reduction": overlap_gain >= protocol["raw_worst_overlap_reduction"],
        "mae_within_guardrail": mae_regression <= protocol["maximum_relative_mae_regression"],
        "adjacency_noninferiority_vs_all_controls": all(c["percentile_95_interval"][0]
            >= -protocol["adjacency_noninferiority_margin"] for c in comparisons.values()),
        "no_budget_or_diversity_regression": all(
            results["geometry"]["benchmark"][metric] + 1e-9 >= v["benchmark"][metric]
            for name, v in results.items() if name != "geometry"
            for metric in ("budget_fit_rate", "mean_diversity_score")),
        "observed_warm_p95_under_limit": results["geometry"]["diagnostics"]["warm_seconds_p95"]
            < protocol["warm_cpu_p95_limit_seconds"],
        "all_arms_five_strict_distinct": engineering["all_arms_five_strict_distinct"],
    }
    report = {"version": VERSION, "seed": geo["config"]["seed"], "stage": "validation",
              "protocol_digest": digest(protocol), "data_identity": data.identity,
              "environment": code_identity(), "repair_budget": asdict(repair),
              "training": {"base": base, "geometry": geo}, "results": results,
              "paired_adjacency": comparisons, "worst_overlap_relative_reduction": overlap_gain,
              "mae_relative_regression": mae_regression, "engineering_gates": engineering,
              "engineering_passed": all(engineering.values()), "research_gates": research,
              "development_signal_passed": all(research.values()), "test_evaluated": False,
              "qualified_model_release": False}
    files["report.json"] = json_bytes(report)
    publish_directory(Path(output), files, {"version": VERSION, "data_identity": data.identity,
                                            "protocol_digest": digest(protocol)})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pair = sub.add_parser("train-pair")
    pair.add_argument("--data", type=Path, required=True)
    pair.add_argument("--output", type=Path, required=True)
    pair.add_argument("--seed", type=int, required=True)
    comparison = sub.add_parser("compare")
    comparison.add_argument("--data", type=Path, required=True)
    comparison.add_argument("--runs", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    comparison.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    protocol = read_protocol()
    if args.command == "train-pair":
        if args.output.exists():
            raise ValueError("Paired geometry output already exists.")
        config = TrainConfig(seed=args.seed, **protocol["training"])
        for arm in ("base", "geometry"):
            train_run(args.data, args.output / arm, config, arm, protocol)
        return 0
    report = compare(args.data, args.runs, args.output, protocol)
    print(json.dumps({k: report[k] for k in ("seed", "engineering_passed",
                      "development_signal_passed", "research_gates")}), flush=True)
    return int(args.enforce and not report["engineering_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
