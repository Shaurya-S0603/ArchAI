"""Concept controls, provenance, integrity and prospective split isolation."""

import hashlib
import json
from copy import deepcopy

import pytest

from archai.datasets.conditioning import (
    load_conditioning_data,
    prepare_conditioning_data,
    previous_program_keys,
    read_protocol,
)
from archai.datasets.schema import geometry_key
from archai.evaluation.cohorts import program_key
from archai.models import DesignBrief


@pytest.fixture
def small_data(tmp_path):
    protocol = deepcopy(read_protocol())
    for rule in protocol["cohorts"].values():
        rule["count"] = 3
    path = tmp_path / "data"
    prepare_conditioning_data(path, protocol)
    return path, protocol


def rewrite_context(path, context):
    raw = json.dumps(context).encode()
    (path / "context.json").write_bytes(raw)
    identity = json.loads((path / "manifest.json").read_text())
    identity["context_sha256"] = hashlib.sha256(raw).hexdigest()
    (path / "manifest.json").write_text(json.dumps(identity))


def test_contexts_splits_and_old_program_exclusions_are_independent(small_data):
    path, protocol = small_data
    identity, manifest, context, rows = load_conditioning_data(path)
    assert context["protocol"] == protocol
    assert len(context["concept_ids"]) == len(rows) == manifest["record_count"]
    assert set(context["concept_ids"].values()) == set(range(5))
    seen, owners = previous_program_keys(), {}
    for split, cohort in context["cohorts"].items():
        for case in cohort["cases"]:
            key = program_key(DesignBrief.from_dict(case["brief"]))
            assert key not in seen
            seen.add(key)
        for row in (r for r in rows if r["split"] == split):
            for key in (row["building_id"], row["group_id"], geometry_key(row, 3)):
                assert key not in owners or owners[key] == split
                owners[key] = split
    assert identity["version"] == "concept-conditioning-v1"
    with pytest.raises(ValueError, match="already exists"):
        prepare_conditioning_data(path, protocol)


def test_context_tampering_and_invalid_tokens_fail_closed(small_data):
    path, _ = small_data
    context = json.loads((path / "context.json").read_text())
    key = next(iter(context["concept_ids"]))
    context["concept_ids"][key] = True
    (path / "context.json").write_text(json.dumps(context))
    with pytest.raises(ValueError, match="checksum"):
        load_conditioning_data(path)
    rewrite_context(path, context)
    with pytest.raises(ValueError, match="mapping"):
        load_conditioning_data(path)


def test_cohort_digest_mismatch_is_rejected(small_data):
    path, _ = small_data
    context = json.loads((path / "context.json").read_text())
    context["cohorts"]["validation"]["cases"][0]["brief"]["budget"] += 1000
    rewrite_context(path, context)
    with pytest.raises(ValueError, match="cohort identity"):
        load_conditioning_data(path)


@pytest.mark.parametrize("change", [{"version": "wrong"}, {"cohorts": {}},
                                   {"cohorts": {s: {"count": True, "seed": 1}
                                                for s in ("train", "validation", "test")}}])
def test_invalid_protocol_rejected(tmp_path, change):
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps({**read_protocol(), **change}))
    with pytest.raises(ValueError):
        read_protocol(path)
