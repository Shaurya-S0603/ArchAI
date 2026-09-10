"""Phase 2F development comparisons and separately opened release qualification."""

import argparse
import json
import tempfile
from pathlib import Path

from archai import create_app
from archai.datasets.schema import encode
from archai.evaluation.benchmark import evaluate_benchmark
from archai.evaluation.cohorts import ROOT, phase2f_cohorts
from archai.evaluation.comparison import compare_reports
from archai.services.cost_estimator import COST_MODEL_VERSION
from archai_ml.diversity import (
    DIVERSITY_VERSION,
    MAXIMUM_SEARCH_NODES,
    REFLOW_FRACTIONS,
    diverse_candidates,
    validate_concepts,
)
from archai_ml.experiment import code_identity, json_bytes, publish_directory
from archai_ml.inference import FROZEN_DATA, FROZEN_STATE
from archai_ml.repair_evaluation import RepairedCandidate, summarize_history


def checked_repair(brief, proposal, config):
    layouts, diagnostics = diverse_candidates(brief, proposal, config)
    validate_concepts(layouts, brief, config.minimum_separation)
    return layouts, diagnostics


def api_smoke(run, brief):
    with tempfile.TemporaryDirectory(prefix="archai-api-") as directory:
        app = create_app({"TESTING": True, "DATABASE": str(Path(directory) / "api.sqlite3"),
                          "ARCHAI_GENERATOR": "experimental-neural", "ARCHAI_MODEL_RUN": str(run)})
        with app.test_client() as client:
            first = client.post("/api/v1/layouts/generate", json=brief.to_dict())
            second = client.post("/api/v1/layouts/generate", json=brief.to_dict())
        data = first.get_json()
        return {"status_ok": first.status_code == second.status_code == 200,
                "experimental_used": data.get("generator", {}).get("used") == "experimental-neural",
                "five_results": len(data.get("results", [])) == 5,
                "repeatable_response": data == second.get_json()}


def run_qualification(run, output, stage="development"):
    if stage not in ("development", "release"):
        raise ValueError("Unknown qualification stage.")
    if Path(output).exists():
        raise ValueError("Qualification output already exists.")
    cohorts, manifest = phase2f_cohorts()
    expected = json.loads((ROOT / "data/benchmarks/phase2f-manifest.json").read_text())
    config = manifest["protocol"]
    if (manifest != expected or config["version"] != DIVERSITY_VERSION
            or config["cost_model_version"] != COST_MODEL_VERSION
            or config["reflow_fractions"] != list(REFLOW_FRACTIONS)
            or config["maximum_search_nodes"] != MAXIMUM_SEARCH_NODES
            or config["minimum_separation"] != .025):
        raise ValueError("Phase 2F protocol, implementation or cohort identity drifted.")
    candidate = RepairedCandidate(run, repairer=checked_repair)
    reference = RepairedCandidate(run, reference=True, repairer=checked_repair)
    if (candidate.training["state_digest"] != FROZEN_STATE
            or candidate.training["dataset_digest"] != FROZEN_DATA):
        raise ValueError("Qualification requires the frozen Phase 2D checkpoint.")
    files, results = {}, {}
    for name in (("development", "validation") if stage == "development" else ("test",)):
        cases = cohorts[name]
        candidate.history.clear()
        reference.history.clear()
        baseline = evaluate_benchmark(cases)
        neural = evaluate_benchmark(cases, candidate, "diverse-neural-v1")
        prior = evaluate_benchmark(cases, reference, "diverse-type-reference-v1")
        comparison = compare_reports(baseline, neural)
        diagnostics = summarize_history(candidate)
        gates = {"comparison": comparison["passed"],
                 "strict_validity": diagnostics["strict_validated_rate"] == 1,
                 "five_distinct": diagnostics["five_distinct_rate"] == 1,
                 "adjacency_gain_ten_points": comparison["deltas"]["mean_adjacency_satisfaction"] >= .1,
                 "observed_warm_cpu_p95_under_five_seconds": diagnostics["cpu_seconds_p95"] < 5}
        results[name] = {"comparison": comparison, "neural_diagnostics": diagnostics,
                         "reference": prior["summary"],
                         "reference_diagnostics": summarize_history(reference),
                         "gates": gates, "passed": all(gates.values())}
        files[f"{name}-neural-cases.json"] = json_bytes(candidate.history)
        files[f"{name}-reference-cases.json"] = json_bytes(reference.history)
        files[f"{name}-benchmark.json"] = json_bytes(neural)
        print(encode({"cohort": name, **results[name]}), flush=True)
    if stage == "release":
        candidate.history.clear()
        for i, case in enumerate(cohorts["stress"]):
            try:
                candidate(case.brief)
            except ValueError:
                pass  # Expected rejection recorded; runtime/programming faults fail qualification.
            if (i + 1) % 100 == 0:
                print(encode({"stress_completed": i + 1}), flush=True)
        stress = summarize_history(candidate)
        gates = {"one_thousand_briefs": stress["cases"] == 1000,
                 "no_failed_briefs": stress["failed_cases"] == 0,
                 "strict_validity": stress["strict_validated_rate"] == 1,
                 "five_distinct": stress["five_distinct_rate"] == 1,
                 "observed_warm_cpu_p95_under_five_seconds": stress["cpu_seconds_p95"] < 5}
        results["stress"] = {**stress, "gates": gates, "passed": all(gates.values())}
        files["stress-cases.json"] = json_bytes(candidate.history)
    api_gates = api_smoke(run, cohorts["development"][0].brief)
    report = {"version": DIVERSITY_VERSION, "stage": stage, "cohorts": manifest,
              "environment": code_identity(), "model_state_digest": FROZEN_STATE,
              "training_dataset_digest": FROZEN_DATA, "results": results, "api_gates": api_gates,
              "engineering_passed": all(r["passed"] for r in results.values()) and all(api_gates.values()),
              "qualified_model_release": False,
              "remaining_requirements": ["independent licensed real-plan evaluation",
                                         "blinded human preference above 60 percent",
                                         "demonstrated neural quality benefit over matched reference"]}
    files["report.json"] = json_bytes(report)
    publish_directory(output, files, {"version": DIVERSITY_VERSION, "stage": stage})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("development", "release"), default="development")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    report = run_qualification(args.run, args.output, args.stage)
    print(encode(report))
    return int(args.enforce and not report["engineering_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
