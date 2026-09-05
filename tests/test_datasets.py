import hashlib
import json
from copy import deepcopy

import pytest

from archai.datasets.__main__ import main
from archai.datasets.pilot import (
    build_pilot,
    evaluation_exclusions,
    layout_record,
    synthetic_source,
)
from archai.datasets.pipeline import (
    assign_splits,
    load_dataset,
    preprocess,
    validate_source,
    write_dataset,
)
from archai.datasets.schema import canonicalize, digest, encode, geometry_key
from archai.datasets.training import batches
from archai.evaluation.dataset import DEFAULT_SEED, build_synthetic_cases
from archai.services.layout_generator import generate_layouts


@pytest.fixture
def raw_plan():
    case = build_synthetic_cases(count=1, seed=98123)[0]
    return layout_record(
        generate_layouts(case.brief)[0], "sample-1", "building-1", "archai-synthetic-roomgraphs-v1"
    )


def prepare(records):
    payload = ("".join(encode(row) + "\n" for row in records)).encode()
    return payload, synthetic_source(payload)


def test_canonical_roundtrip_and_order_invariance(raw_plan):
    row = canonicalize(raw_plan)
    assert row == json.loads(encode(row))
    reordered = deepcopy(raw_plan)
    reordered["rooms"].reverse()
    for i, room in enumerate(reordered["rooms"]):
        room["id"] = f"arbitrary-{i}"
    assert canonicalize(reordered) == row
    bw, bh = row["footprint_m"]
    assert all(0 <= value <= 1 for room in row["rooms"] for value in room["box"])
    assert bw > 0 and bh > 0 and row["adjacency"]


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r: r.update(units="ft"), "unsupported_units"),
        (lambda r: r.update(schema_version=2), "unsupported_schema"),
        (lambda r: r.update(schema_version=True), "unsupported_schema"),
        (lambda r: r.update(address="private"), "invalid_record_fields"),
        (lambda r: r.update(id="../../secret"), "invalid_identifier"),
        (lambda r: r.update(rooms=[]), "unsupported_room_count"),
        (lambda r: r["rooms"][0].update(type="unknown"), "unsupported_room_type"),
        (lambda r: r["rooms"][0].update(label="private"), "invalid_room_fields"),
        (lambda r: r["rooms"][0]["box"].update(width=float("nan")), "invalid_number"),
        (lambda r: r["rooms"][0]["box"].update(width=True), "invalid_number"),
        (lambda r: r["rooms"][0]["box"].update(width="3"), "invalid_number"),
        (lambda r: r["rooms"][0]["box"].update(width=0), "invalid_dimensions"),
        (lambda r: r["rooms"][0]["box"].update(width=0.01), "minimum_area"),
        (lambda r: r["rooms"][0]["box"].update(x=-5), "outside_footprint"),
        (lambda r: r["rooms"][0].update(box={"polygon": []}), "unsupported_rectangle"),
        (lambda r: r["rooms"][1].update(id=r["rooms"][0]["id"]), "duplicate_room_id"),
        (lambda r: r["rooms"][1].update(box=r["rooms"][0]["box"]), "overlap"),
    ],
)
def test_rejects_unsupported_or_invalid_geometry(raw_plan, change, reason):
    change(raw_plan)
    with pytest.raises(ValueError, match=reason):
        canonicalize(raw_plan)


def test_disconnected_plan_rejected(raw_plan):
    for room in raw_plan["rooms"]:
        room["box"]["x"] *= 3
        room["box"]["y"] *= 3
    for key in raw_plan["footprint"]:
        raw_plan["footprint"][key] *= 3
    with pytest.raises(ValueError, match="disconnected"):
        canonicalize(raw_plan)


def test_fingerprint_ignores_scale_translation_and_mirror(raw_plan):
    first = canonicalize(raw_plan)
    moved = deepcopy(raw_plan)
    for item in [moved["footprint"], *[r["box"] for r in moved["rooms"]]]:
        for key in item:
            item[key] *= 2
        item["x"] += 12
        item["y"] += 9
    assert geometry_key(canonicalize(moved)) == geometry_key(first)
    mirror = deepcopy(first)
    for room in mirror["rooms"]:
        x, y, w, h = room["box"]
        room["box"] = [1 - x - w, y, w, h]
    assert geometry_key(mirror) == geometry_key(first)
    for room in mirror["rooms"]:
        x, y, w, h = room["box"]
        room["box"] = [y, x, h, w]
    mirror["footprint_m"].reverse()
    assert geometry_key(mirror) == geometry_key(first)
    stretched = {
        **deepcopy(first),
        "footprint_m": [first["footprint_m"][0] * 2, first["footprint_m"][1]],
    }
    assert geometry_key(stretched) != geometry_key(first)


@pytest.mark.parametrize(
    "permission",
    [
        "training",
        "derivatives",
        "redistribution",
        "checkpoint_distribution",
        "privacy",
    ],
)
def test_quarantined_source_cannot_enter_pipeline(raw_plan, permission):
    payload, source = prepare([raw_plan])
    source["origin"] = "external"
    source["review"][permission] = False
    with pytest.raises(ValueError, match="not admitted"):
        preprocess(payload, source)


def test_source_review_and_integrity_required(raw_plan):
    payload, source = prepare([raw_plan])
    for key, value in [("sha256", "0" * 64), ("license", ""), ("origin", "user-project")]:
        changed = {**source, key: value}
        with pytest.raises(ValueError):
            validate_source(changed, payload)
    for key in ("reviewer", "evidence", "date"):
        changed = deepcopy(source)
        changed["review"].pop(key)
        with pytest.raises(ValueError):
            validate_source(changed, payload)
    with pytest.raises(ValueError):
        validate_source({}, payload)


def test_rejection_counts_and_duplicate_ids(raw_plan):
    wrong_source = {**raw_plan, "id": "wrong-source", "source_id": "elsewhere"}
    bad_units = {**raw_plan, "id": "bad-units", "units": "mm"}
    duplicate = {**raw_plan, "id": "copy", "building_id": "another-building"}
    payload, source = prepare([raw_plan, wrong_source, bad_units, duplicate])
    payload += b"not-json\n"
    source["sha256"] = hashlib.sha256(payload).hexdigest()
    rows, report = preprocess(payload, source)
    assert len(rows) == 1
    assert report["input_records"] == 5
    assert report["exact_duplicates_removed"] == 1
    assert report["rejection_reasons"] == {
        "source_mismatch": 1,
        "unsupported_units": 1,
        "invalid_json": 1,
    }
    with pytest.raises(ValueError, match="duplicate_record_id"):
        preprocess(*prepare([raw_plan, raw_plan]))
    with pytest.raises(ValueError, match="No admissible"):
        preprocess(*prepare([bad_units]))


def test_transitive_duplicate_groups_prevent_building_leakage(raw_plan):
    a = canonicalize(raw_plan)
    b = {**deepcopy(a), "id": "b", "building_id": "building-2"}
    c = {**deepcopy(b), "id": "c"}
    c["rooms"][0]["box"][0] += 0.002
    d = {**deepcopy(c), "id": "d", "building_id": "building-3"}
    rows = assign_splits([a, b, c, d], 10)
    assert len({r["group_id"] for r in rows}) == 1
    assert rows == assign_splits([d, c, a, b], 10)
    nearby = {**deepcopy(a), "id": "near", "building_id": "unrelated"}
    nearby["rooms"][0]["box"][0] += 0.000001
    assert geometry_key(nearby, 3) == geometry_key(a, 3)
    assert len({r["split"] for r in assign_splits([a, nearby], 15)}) == 1


def test_evaluation_exclusion_blocks_whole_building(raw_plan):
    variant = deepcopy(raw_plan)
    variant["id"] = "variant"
    variant["rooms"][1]["type"] = "storage"
    other = deepcopy(variant)
    other["id"] = "allowed"
    other["building_id"] = "elsewhere"
    other["rooms"][2]["type"] = "storage"
    rows, report = preprocess(
        *prepare([raw_plan, variant, other]),
        excluded_keys={geometry_key(canonicalize(raw_plan), 3)},
    )
    assert [r["id"] for r in rows] == ["allowed"]
    assert report["rejection_reasons"] == {"evaluation_geometry_overlap": 2}


def test_dataset_writes_are_immutable_and_verified(tmp_path, raw_plan):
    payload, source = prepare([raw_plan])
    rows, report = preprocess(payload, source)
    path = tmp_path / "dataset-v1"
    manifest = write_dataset(path, rows, report, source)
    assert load_dataset(path) == (manifest, rows)
    with pytest.raises(ValueError, match="already exists"):
        write_dataset(path, rows, report, source)
    (path / "records.jsonl").write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_dataset(path)


def test_loader_detects_leakage_even_with_rehashed_content(tmp_path, raw_plan):
    payload, source = prepare([raw_plan])
    rows, report = preprocess(payload, source)
    path = tmp_path / "dataset"
    write_dataset(path, rows, report, source)
    rows.append(
        {**rows[0], "id": "leaked-copy", "split": "test" if rows[0]["split"] != "test" else "train"}
    )
    data = "".join(encode(r) + "\n" for r in rows)
    (path / "records.jsonl").write_text(data)
    manifest = json.loads((path / "manifest.json").read_text())
    manifest.update(record_count=2, records_digest=digest(rows))
    manifest["files"]["records.jsonl"] = hashlib.sha256(data.encode()).hexdigest()
    (path / "manifest.json").write_text(encode(manifest))
    with pytest.raises(ValueError, match="leakage"):
        load_dataset(path)


def test_pilot_reproducibility_splits_batches_and_cli(tmp_path, capsys):
    first, second = tmp_path / "first", tmp_path / "second"
    report = build_pilot(first, count=40)
    assert main(["pilot", "--output", str(second), "--count", "40"]) == 0
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert set(report["split_counts"]) == {"train", "validation", "test"}
    ids = {}
    for split in ("train", "validation", "test"):
        data = list(batches(first, split, batch_size=7, seed=9))
        ids[split] = {i for b in data for i in b["ids"]}
        assert data == list(batches(first, split, batch_size=7, seed=9))
        for b in data:
            for i, mask in enumerate(b["room_mask"]):
                assert len(mask) == len(b["type_ids"][i]) == len(b["target_boxes"][i])
                n = sum(mask)
                assert all(t == 0 for t in b["type_ids"][i][n:])
                graph = b["target_adjacency"][i]
                assert all(
                    graph[x][y] == graph[y][x] for x in range(len(mask)) for y in range(len(mask))
                )
    assert ids["train"].isdisjoint(ids["test"] | ids["validation"])
    assert main(["validate", str(first)]) == 0
    assert "records_digest" in capsys.readouterr().out
    for split, size in [("all", 4), ("train", 0), ("train", True)]:
        with pytest.raises(ValueError):
            list(batches(first, split, size))
    with pytest.raises(ValueError, match="evaluation seed"):
        build_pilot(tmp_path / "forbidden", seed=DEFAULT_SEED)
    with pytest.raises(SystemExit) as error:
        main(["validate", str(tmp_path / "missing")])
    assert error.value.code == 1


def test_ingest_cli_with_reviewed_source(tmp_path, raw_plan):
    payload, source = prepare([raw_plan])
    (tmp_path / "raw.jsonl").write_bytes(payload)
    (tmp_path / "source.json").write_text(encode(source))
    assert (
        main(
            [
                "ingest",
                "--input",
                str(tmp_path / "raw.jsonl"),
                "--source",
                str(tmp_path / "source.json"),
                "--output",
                str(tmp_path / "processed"),
            ]
        )
        == 0
    )


def test_pilot_excludes_every_frozen_evaluation_brief_and_geometry(tmp_path):
    from archai.datasets.pilot import PROJECT_ROOT

    briefs, keys = evaluation_exclusions(PROJECT_ROOT / "data/benchmarks/v1")
    build_pilot(tmp_path / "pilot", count=10)
    _, rows = load_dataset(tmp_path / "pilot")
    assert len(briefs) == 100
    assert all(geometry_key(r, 3) not in keys for r in rows)
    assert all(r["building_id"].removeprefix("brief-") not in briefs for r in rows)
