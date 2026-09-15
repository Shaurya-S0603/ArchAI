"""Fresh, context-labelled synthetic data; context is selected before geometry.

Concept tokens identify the five existing generator controls. They are not
inferred from observed boxes or from a model's success on a case. The holdout is
prepared for integrity/deduplication but never scored by this development step.
"""

import hashlib
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from archai.datasets.pilot import layout_record, synthetic_source
from archai.datasets.pipeline import load_dataset, preprocess, write_dataset
from archai.datasets.schema import canonicalize, digest, encode, geometry_key
from archai.evaluation.cohorts import ROOT, phase2f_cohorts, program_key
from archai.evaluation.dataset import BenchmarkCase, build_synthetic_cases, dataset_digest
from archai.models import DesignBrief
from archai.services.layout_generator import VARIATIONS, generate_layouts

VERSION = "concept-conditioning-v1"
SOURCE = "archai-synthetic-conditioned-v1"
CONFIG_PATH = ROOT / "ml/configs/phase2g-v1.json"
CONCEPT_NAMES = [v[0] for v in VARIATIONS]


def read_protocol(path=CONFIG_PATH):
    config = json.loads(Path(path).read_text())
    if config.get("version") != VERSION or set(config.get("cohorts", {})) != {
        "train", "validation", "test"
    }:
        raise ValueError("Unsupported conditioning protocol.")
    for rule in config["cohorts"].values():
        if (set(rule) != {"count", "seed"} or type(rule["count"]) is not int
                or not 1 <= rule["count"] <= 1000 or type(rule["seed"]) is not int
                or not 0 <= rule["seed"] < 2**32):
            raise ValueError("Invalid conditioning cohort configuration.")
    return config


def previous_program_keys():
    keys = {program_key(c.brief) for count, seed in ((100, 20260903), (120, 20260905),
                                                   (1000, 20260907))
            for c in build_synthetic_cases(count, seed)}
    previous, _ = phase2f_cohorts()
    keys.update(program_key(c.brief) for cohort in previous.values() for c in cohort)
    return keys


def prepare_conditioning_data(destination, config=None):
    """Admit synthetic targets, exclude old programs and group all five controls.

The existing geometry validator, source admission, duplicate grouping and dataset
loader remain authoritative. Cross-cohort near-duplicate geometry excludes the
entire later brief before any model is trained; exclusion counts are published.
"""
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Conditioning dataset already exists.")
    config = config or read_protocol()
    seen = previous_program_keys()
    old_count = len(seen)
    geometry_owners, contexts, split_by_id, cohorts, raw = {}, {}, {}, {}, []
    for split in ("train", "validation", "test"):
        rule = config["cohorts"][split]
        selected, excluded_programs, excluded_geometry = [], 0, 0
        for batch in range(20):
            for candidate in build_synthetic_cases(1000, rule["seed"] + batch * 100000):
                key = program_key(candidate.brief)
                if key in seen:
                    excluded_programs += 1
                    continue
                # Select the control by generator ID, independent of score sorting.
                layouts = {layout.id: layout for layout in generate_layouts(candidate.brief)}
                case_id = f"phase2g-{split}-{len(selected) + 1:04d}"
                records = [layout_record(layouts[f"archai-v{i + 1}"],
                                         f"{case_id}-concept-{i}", key, SOURCE)
                           for i in range(5)]
                fingerprints = [geometry_key(canonicalize(r), 3) for r in records]
                if any(g in geometry_owners and geometry_owners[g] != split
                       for g in fingerprints):
                    excluded_geometry += 1
                    continue
                seen.add(key)
                geometry_owners.update({g: split for g in fingerprints})
                for i, record in enumerate(records):
                    contexts[record["id"]] = i
                    split_by_id[record["id"]] = split
                raw.extend(records)
                selected.append(BenchmarkCase(case_id, split, candidate.brief))
                if len(selected) == rule["count"]:
                    break
            if len(selected) == rule["count"]:
                break
        if len(selected) != rule["count"]:
            raise ValueError("Unable to fill unique conditioning cohort.")
        cohorts[split] = {"count": len(selected), "sha256": dataset_digest(selected),
                          "excluded_program_collisions": excluded_programs,
                          "excluded_geometry_collisions": excluded_geometry,
                          "cases": [c.to_dict() for c in selected]}
    payload = ("".join(encode(r) + "\n" for r in raw)).encode()
    source = synthetic_source(payload)
    source.update(id=SOURCE, version="1")
    source["review"]["date"] = "2026-09-12"
    source["limitations"] += " Concept IDs select existing teacher controls, not new topologies."
    rows, report = preprocess(payload, source, seed=20260912)
    group_splits = {}
    for row in rows:
        split = split_by_id[row["id"]]
        if row["group_id"] in group_splits and group_splits[row["group_id"]] != split:
            raise ValueError("Conditioning duplicate group spans cohorts.")
        group_splits[row["group_id"]] = split
        row["split"] = split
    report.update(split_counts=dict(Counter(r["split"] for r in rows)), records_digest=digest(rows))
    context = {"version": VERSION, "protocol": config, "concept_names": CONCEPT_NAMES,
               "old_programs_excluded": old_count, "cohorts": cohorts,
               "concept_ids": {r["id"]: contexts[r["id"]] for r in rows}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".archai-conditioning-", dir=destination.parent))
    try:
        write_dataset(stage / "dataset", rows, report, source, seed=20260912)
        context_bytes = (encode(context) + "\n").encode()
        (stage / "context.json").write_bytes(context_bytes)
        identity = {"version": VERSION, "context_sha256": hashlib.sha256(context_bytes).hexdigest(),
                    "dataset_manifest_sha256": hashlib.sha256(
                        (stage / "dataset/manifest.json").read_bytes()).hexdigest()}
        (stage / "manifest.json").write_text(encode(identity) + "\n")
        load_conditioning_data(stage)
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {**identity, "report": report,
            "cohorts": {k: {a: b for a, b in v.items() if a != "cases"}
                        for k, v in cohorts.items()}}


def load_conditioning_data(directory):
    directory = Path(directory)
    identity = json.loads((directory / "manifest.json").read_text())
    if identity.get("version") != VERSION:
        raise ValueError("Unsupported conditioning data version.")
    for name, field in (("context.json", "context_sha256"),
                         ("dataset/manifest.json", "dataset_manifest_sha256")):
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != identity.get(field):
            raise ValueError("Conditioning data checksum mismatch.")
    manifest, rows = load_dataset(directory / "dataset")
    source = json.loads((directory / "dataset/source.json").read_text())
    if (source.get("origin") != "synthetic" or source.get("id") != SOURCE
            or any(source.get("review", {}).get(key) is not True for key in
                   ("training", "derivatives", "redistribution", "checkpoint_distribution", "privacy"))):
        raise ValueError("Conditioning requires the admitted synthetic source.")
    context = json.loads((directory / "context.json").read_text())
    if (context.get("version") != VERSION or context.get("concept_names") != CONCEPT_NAMES
            or set(context.get("concept_ids", {})) != {r["id"] for r in rows}
            or any(type(c) is not int or not 0 <= c < 5 for c in context["concept_ids"].values())):
        raise ValueError("Invalid concept context mapping.")
    programs, by_building = set(), {}
    for split in ("train", "validation", "test"):
        cohort = context["cohorts"][split]
        cases = [BenchmarkCase(c["id"], split, DesignBrief.from_dict(c["brief"]))
                 for c in cohort["cases"]]
        if len(cases) != cohort["count"] or dataset_digest(cases) != cohort["sha256"]:
            raise ValueError("Conditioning cohort identity mismatch.")
        for case in cases:
            key = program_key(case.brief)
            if key in programs:
                raise ValueError("Cross-cohort model input leakage.")
            programs.add(key)
            by_building[key] = split
    if any(by_building.get(r["building_id"]) != r["split"] for r in rows):
        raise ValueError("Conditioning target split mismatch.")
    if context["protocol"] == read_protocol():
        expected = json.loads((ROOT / "data/benchmarks/phase2g-manifest.json").read_text())
        actual = {"version": VERSION, "records_digest": manifest["records_digest"],
                  "context_sha256": identity["context_sha256"],
                  "cohorts": {k: {f: v[f] for f in ("count", "sha256")}
                              for k, v in context["cohorts"].items()}}
        if actual != expected:
            raise ValueError("Frozen Phase 2G data or cohort identity drifted.")
    return identity, manifest, context, rows
