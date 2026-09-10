import json
import sys
from collections import Counter

import pytest

from archai.evaluation.__main__ import main
from archai.evaluation.benchmark import (
    DEFAULT_THRESHOLDS,
    adjacency_satisfaction_score,
    evaluate_benchmark,
    layout_diversity_score,
    program_match_score,
    report_to_markdown,
)
from archai.evaluation.candidates import get_candidate
from archai.evaluation.comparison import compare_reports
from archai.evaluation.comparison import main as comparison_main
from archai.evaluation.dataset import (
    BENCHMARK_SCHEMA_VERSION,
    BenchmarkCase,
    build_synthetic_cases,
    dataset_digest,
    load_benchmark,
    write_benchmark,
)
from archai.models import DesignBrief
from archai.services.layout_generator import generate_layouts


def test_synthetic_benchmark_is_deterministic_and_balanced():
    first = build_synthetic_cases()
    second = build_synthetic_cases()

    assert len(first) == 100
    assert dataset_digest(first) == dataset_digest(second)
    assert Counter(case.split for case in first) == {
        "development": 60,
        "validation": 20,
        "test": 20,
    }
    assert len({case.id for case in first}) == 100


def test_benchmark_round_trip_and_digest_validation(tmp_path):
    destination = tmp_path / "benchmark"
    manifest = write_benchmark(destination, count=12)
    loaded_manifest, cases = load_benchmark(destination)

    assert loaded_manifest == manifest
    assert len(cases) == 12

    rows = (destination / "briefs.jsonl").read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0])
    first["id"] = "changed"
    rows[0] = json.dumps(first)
    (destination / "briefs.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        load_benchmark(destination)


def test_benchmark_case_rejects_unknown_schema(brief):
    with pytest.raises(ValueError, match="schema version"):
        BenchmarkCase.from_dict(
            {
                "schema_version": BENCHMARK_SCHEMA_VERSION + 1,
                "id": "future-case",
                "split": "test",
                "brief": brief,
            }
        )


def test_program_and_diversity_metrics(brief):
    design_brief = DesignBrief.from_dict(brief)
    layouts = generate_layouts(design_brief)

    assert program_match_score(layouts[0], design_brief) == 1.0
    assert 0 < adjacency_satisfaction_score(layouts[0], design_brief) <= 1
    assert layout_diversity_score([layouts[0], layouts[0]]) == 0.0
    assert layout_diversity_score(layouts) > 0


def test_evaluation_report_exposes_candidate_comparison_metrics():
    report = evaluate_benchmark(build_synthetic_cases(count=8))

    assert report["candidate"] == "deterministic-baseline"
    assert report["summary"]["case_count"] == 8
    assert set(DEFAULT_THRESHOLDS) == set(report["gates"])
    assert report["summary"]["program_match_rate"] == 1.0
    assert "Overall gate" in report_to_markdown(report)


def test_evaluation_records_generation_failures():
    def failing_generator(_brief):
        raise ValueError("candidate failed")

    report = evaluate_benchmark(build_synthetic_cases(count=1), generator=failing_generator)

    assert report["passed"] is False
    assert report["summary"]["case_success_rate"] == 0.0
    assert report["cases"][0]["error"] == "candidate failed"


def test_benchmark_cli_writes_reports(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset"
    json_report = tmp_path / "reports" / "baseline.json"
    markdown_report = tmp_path / "reports" / "baseline.md"
    write_benchmark(dataset, count=4)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "archai-evaluate",
            "--dataset",
            str(dataset),
            "--json",
            str(json_report),
            "--markdown",
            str(markdown_report),
            "--enforce",
        ],
    )

    assert main() == 0
    assert json.loads(json_report.read_text(encoding="utf-8"))["passed"] is True
    assert "Regression gates" in markdown_report.read_text(encoding="utf-8")


def test_candidate_registry_and_comparison_require_matching_datasets():
    with pytest.raises(ValueError, match="Unknown generator"):
        get_candidate("not-a-candidate")

    baseline = evaluate_benchmark(build_synthetic_cases(count=1))
    candidate = dict(baseline)
    candidate["dataset_sha256"] = "different"
    with pytest.raises(ValueError, match="same benchmark"):
        compare_reports(baseline, candidate)


def test_solver_comparison_cli_writes_reports(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset"
    json_report = tmp_path / "reports" / "comparison.json"
    markdown_report = tmp_path / "reports" / "comparison.md"
    write_benchmark(dataset, count=4)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "archai-compare",
            "--dataset",
            str(dataset),
            "--json",
            str(json_report),
            "--markdown",
            str(markdown_report),
            "--enforce",
        ],
    )

    assert comparison_main() == 0
    assert json.loads(json_report.read_text(encoding="utf-8"))["passed"] is True
    assert "Promotion gate: **PASS**" in markdown_report.read_text(encoding="utf-8")
