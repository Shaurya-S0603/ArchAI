"""The default install and rejected experimental outputs preserve the API contract."""

import sys

import pytest

from archai import create_app
from archai.services import generation_engine


def test_default_engine_and_request_cannot_enable_model(client, brief, monkeypatch):
    def forbidden(*_):
        raise AssertionError("Default app must not load ML.")
    monkeypatch.setattr(generation_engine, "load_experimental_engine", forbidden)
    brief.update(generator="experimental-neural", model_run="/untrusted/path")
    response = client.post("/api/v1/layouts/generate", json=brief)
    assert response.status_code == 200
    assert response.get_json()["generator"] == {
        "requested": "deterministic-baseline", "used": "deterministic-baseline",
        "fallback": False, "reason": None}


@pytest.mark.parametrize("error", [ImportError("torch absent"), OSError("private/checkpoint"),
                                    ValueError("bad weights"), RuntimeError("bad tensors")])
def test_unavailable_engine_falls_back_without_exposing_paths(tmp_path, monkeypatch, brief, error):
    def unavailable(_):
        raise error
    monkeypatch.setattr(generation_engine, "load_experimental_engine", unavailable)
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "db.sqlite3"),
                      "ARCHAI_GENERATOR": "experimental-neural", "ARCHAI_MODEL_RUN": "/private/run"})
    response = app.test_client().post("/api/v1/layouts/generate", json=brief)
    data = response.get_json()
    assert response.status_code == 200 and len(data["results"]) == 5
    assert data["generator"]["fallback"] is True
    assert data["generator"]["reason"] == "engine_unavailable"
    assert b"private" not in response.data


@pytest.mark.parametrize("fault", ["shortfall", "exception", "overlap"])
def test_bad_candidate_falls_back(app, client, brief, fault):
    def bad_candidate(program):
        if fault == "exception":
            raise RuntimeError("internal detail")
        layouts = generation_engine.generate_layouts(program)
        if fault == "shortfall":
            return layouts[:2]
        layouts[0].rooms[0].width = 999
        return layouts
    app.extensions["archai_generator"] = {
        "requested": "experimental-neural", "engine": bad_candidate, "reason": None}
    data = client.post("/api/v1/layouts/generate", json=brief).get_json()
    assert len(data["results"]) == 5
    assert data["generator"]["used"] == "deterministic-baseline"
    assert data["generator"]["reason"] == "candidate_rejected"


def test_unknown_engine_setting_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown"):
        create_app({"DATABASE": str(tmp_path / "db.sqlite3"), "ARCHAI_GENERATOR": "typo"})


def test_default_factory_does_not_import_torch(tmp_path):
    before = "torch" in sys.modules
    create_app({"DATABASE": str(tmp_path / "db.sqlite3"), "ARCHAI_GENERATOR": "deterministic-baseline"})
    assert ("torch" in sys.modules) == before
