"""Qualification must bind the model/protocol and report failures without hiding them."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

torch = pytest.importorskip("torch")

from archai.datasets.pilot import build_pilot
from archai.evaluation.cohorts import phase2f_cohorts
from archai_ml import inference, qualification
from archai_ml.experiment import TrainConfig, train


@pytest.fixture(scope="module")
def small_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("qualification-model")
    build_pilot(root / "pilot", count=40)
    report = train(root / "pilot", root / "run", TrainConfig(epochs=1, hidden_size=8, layers=1))
    return root / "run", report


@pytest.fixture
def admitted(small_run, monkeypatch):
    run, report = small_run
    for module in (inference, qualification):
        monkeypatch.setattr(module, "FROZEN_STATE", report["state_digest"])
        monkeypatch.setattr(module, "FROZEN_DATA", report["dataset_digest"])
    return run


def test_inference_rejects_missing_and_unqualified_checkpoint(small_run):
    with pytest.raises(ValueError, match="requires"):
        inference.NeuralEngine(None)
    with pytest.raises(ValueError, match="mismatch"):
        inference.NeuralEngine(small_run[0])


def test_actual_model_serving_is_repeatable_across_threads_and_keeps_no_history(admitted):
    engine = inference.NeuralEngine(admitted)
    brief = phase2f_cohorts()[0]["development"][0].brief
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(engine, [brief, brief]))
    assert [l.to_dict() for l in results[0]] == [l.to_dict() for l in results[1]]
    assert not hasattr(engine, "history")
    assert all(qualification.api_smoke(admitted, brief).values())


def test_qualification_end_to_end_artifacts_and_stress_failure_reporting(admitted, tmp_path, monkeypatch):
    cohorts, manifest = phase2f_cohorts()
    # Small injected cohort for exercising the release path, never a release claim.
    tiny = {key: value[:1] for key, value in cohorts.items()}
    monkeypatch.setattr(qualification, "phase2f_cohorts", lambda: (tiny, manifest))
    report = qualification.run_qualification(admitted, tmp_path / "release", "release")
    assert report["qualified_model_release"] is False
    assert report["results"]["stress"]["gates"]["one_thousand_briefs"] is False
    assert report["engineering_passed"] is False
    assert report["results"]["test"]["neural_diagnostics"]["cases"] == 1
    assert all(report["api_gates"].values())
    assert len(json.loads((tmp_path / "release/stress-cases.json").read_text())) == 1
    code = qualification.main(["--run", str(admitted), "--output", str(tmp_path / "development"),
                               "--enforce"])
    saved = json.loads((tmp_path / "development/report.json").read_text())
    assert code == int(not saved["engineering_passed"])
    assert set(saved["results"]) == {"development", "validation"}
    with pytest.raises(ValueError, match="already exists"):
        qualification.run_qualification(admitted, tmp_path / "release")
    with pytest.raises(ValueError, match="Unknown"):
        qualification.run_qualification(admitted, tmp_path / "bad", "bad")
    monkeypatch.setattr(qualification, "FROZEN_STATE", "wrong-state")
    with pytest.raises(ValueError, match="frozen"):
        qualification.run_qualification(admitted, tmp_path / "wrong-state")
    manifest["excluded_programs"] += 1
    with pytest.raises(ValueError, match="drifted"):
        qualification.run_qualification(admitted, tmp_path / "drift")
