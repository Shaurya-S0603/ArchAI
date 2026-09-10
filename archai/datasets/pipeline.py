"""Admission, deterministic deduplication, grouped splits and integrity-checked IO."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

from archai.datasets.preview import contact_sheet
from archai.datasets.schema import (
    ROOM_TYPES,
    SCHEMA_VERSION,
    SPLITS,
    canonicalize,
    digest,
    encode,
    geometry_key,
    identifier,
    validate_canonical,
)


def validate_source(source: dict, payload: bytes) -> None:
    """Validate a recorded review; metadata is evidence, not automatic legal approval."""
    fields = {
        "schema_version",
        "id",
        "version",
        "origin",
        "license",
        "source_url",
        "sha256",
        "review",
        "coverage",
        "limitations",
    }
    if not isinstance(source, dict) or set(source) != fields:
        raise ValueError("Source manifest fields are incomplete or unsupported.")
    for key in ("id", "version"):
        identifier(source[key])
    if (
        type(source["schema_version"]) is not int
        or source["schema_version"] != SCHEMA_VERSION
        or source["origin"]
        not in {
            "synthetic",
            "external",
        }
    ):
        raise ValueError("Unsupported source schema or origin.")
    for key in ("license", "source_url", "coverage", "limitations"):
        if not isinstance(source[key], str) or not source[key].strip():
            raise ValueError(f"Source requires {key}.")
    review = source["review"]
    if not isinstance(review, dict):
        raise ValueError("Source requires a recorded review.")
    for key in ("training", "derivatives", "redistribution", "checkpoint_distribution", "privacy"):
        if review.get(key) is not True:
            raise ValueError(f"Source not admitted: {key} permission/review missing.")
    for key in ("reviewer", "evidence"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError(f"Source requires review {key}.")
    try:
        date.fromisoformat(review["date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Source requires an ISO review date.") from exc
    if source["sha256"] != hashlib.sha256(payload).hexdigest():
        raise ValueError("Source checksum mismatch.")


def assign_splits(records: list[dict], seed: int) -> list[dict]:
    """Union buildings and duplicate buckets BEFORE removing exact duplicates."""
    parent = list(range(len(records)))

    def root(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owners = {}
    for i, row in enumerate(records):
        keys = (
            ("building", row["source_id"], row["building_id"]),
            ("near", geometry_key(row, 3)),
            ("exact", geometry_key(row)),
        )
        for key in keys:
            if key in owners:
                parent[root(i)] = root(owners[key])
            owners[key] = i
    groups = {}
    for i, row in enumerate(records):
        groups.setdefault(root(i), []).append(row)
    output = []
    for group in groups.values():
        group_id = digest(sorted({(r["source_id"], r["building_id"]) for r in group}))
        bucket = int(digest([seed, group_id])[:8], 16) / 2**32
        split = "train" if bucket < 0.8 else "validation" if bucket < 0.9 else "test"
        output.extend({**r, "group_id": group_id, "split": split} for r in group)
    return sorted(output, key=lambda r: r["id"])


def preprocess(
    payload: bytes, source: dict, seed: int = 20260905, excluded_keys: set[str] | None = None
) -> tuple[list[dict], dict]:
    validate_source(source, payload)
    records, rejected, seen = [], Counter(), set()
    lines = payload.decode("utf-8").splitlines()
    for line in lines:
        try:
            raw = json.loads(line)
            row = canonicalize(raw)
            if row["source_id"] != source["id"]:
                raise ValueError("source_mismatch")
            records.append(row)
        except (ValueError, TypeError) as exc:
            reason = "invalid_json" if isinstance(exc, json.JSONDecodeError) else str(exc)
            rejected[reason] += 1
    for row in records:
        if row["id"] in seen:
            raise ValueError("Ambiguous duplicate_record_id; use unique sample IDs.")
        seen.add(row["id"])
    grouped = assign_splits(records, seed)
    blocked_groups = {
        r["group_id"] for r in grouped if excluded_keys and geometry_key(r, 3) in excluded_keys
    }
    unique = {}
    for row in grouped:
        if row["group_id"] in blocked_groups:
            rejected["evaluation_geometry_overlap"] += 1
        else:
            unique.setdefault(geometry_key(row), row)
    rows = sorted(unique.values(), key=lambda r: r["id"])
    excluded_count = rejected["evaluation_geometry_overlap"]
    if not excluded_count:
        del rejected["evaluation_geometry_overlap"]
    if not rows:
        raise ValueError("No admissible plans; nothing was written.")
    report = {
        "schema_version": SCHEMA_VERSION,
        "input_records": len(lines),
        "valid_records": len(records),
        "accepted_records": len(rows),
        "exact_duplicates_removed": len(records) - excluded_count - len(rows),
        "rejected_records": sum(rejected.values()),
        "rejection_reasons": dict(rejected),
        "split_counts": dict(Counter(r["split"] for r in rows)),
        "group_count": len({r["group_id"] for r in rows}),
        "room_type_counts": dict(Counter(room["type"] for r in rows for room in r["rooms"])),
        "evaluation_exclusion_keys": len(excluded_keys or ()),
        "records_digest": digest(rows),
    }
    return rows, report


def data_card(report: dict, source: dict) -> str:
    return (
        "# Phase 2C dataset report\n\n"
        f"Source: `{source['id']}` version `{source['version']}`; "
        f"origin: {source['origin']}; license: {source['license']}. "
        "Full provenance and admission evidence are in `source.json`.\n\n"
        f"Accepted plans: {report['accepted_records']}; "
        f"exact duplicates removed: {report['exact_duplicates_removed']}; "
        f"rejected: {report['rejected_records']}.\n\n"
        "| Split | Plans |\n|---|---:|\n"
        + "".join(f"| {s} | {report['split_counts'].get(s, 0)} |\n" for s in SPLITS)
        + f"\nBuilding/duplicate groups: {report['group_count']}.\n\n"
        "Only rectangular rooms in metres are supported. Adjacency means a shared "
        "boundary of at least 0.8 m; it does not establish a door or accessible route. "
        "Edge clusters spanning at most 2 mm are consolidated before validation. "
        "Coarse duplicate buckets can miss near copies across rounding boundaries. "
        "Synthetic pilot performance does not establish real-plan generalization.\n\n"
        f"Records SHA-256: `{report['records_digest']}`\n\n"
        "![Canonical geometry contact sheet](preview.png)\n"
    )


def write_dataset(
    destination: Path, rows: list[dict], report: dict, source: dict, seed: int = 20260905
) -> dict:
    """Stage in the same filesystem; publish a new immutable directory only."""
    if destination.exists():
        raise ValueError("Destination already exists; use a new dataset version/directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".archai-dataset-", dir=destination.parent))
    try:
        files = {
            "records.jsonl": "".join(encode(row) + "\n" for row in rows),
            "report.json": encode(report) + "\n",
            "DATA_CARD.md": data_card(report, source),
            "source.json": encode(source) + "\n",
        }
        files = {name: content.encode() for name, content in files.items()}
        files["preview.png"] = contact_sheet(rows)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "seed": seed,
            "taxonomy": list(ROOM_TYPES),
            "source_id": source["id"],
            "records_digest": digest(rows),
            "record_count": len(rows),
            "files": {p: hashlib.sha256(b).hexdigest() for p, b in files.items()},
        }
        for name, content in {**files, "manifest.json": (encode(manifest) + "\n").encode()}.items():
            (stage / name).write_bytes(content)
        load_dataset(stage)
        stage.rename(destination)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def load_dataset(directory: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("taxonomy") != list(
        ROOM_TYPES
    ):
        raise ValueError("Unsupported dataset version or taxonomy.")
    expected = {"records.jsonl", "report.json", "DATA_CARD.md", "source.json", "preview.png"}
    if set(manifest.get("files", {})) != expected:
        raise ValueError("Invalid dataset file manifest.")
    for name, sha in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != sha:
            raise ValueError(f"Dataset checksum mismatch: {name}")
    rows = [json.loads(line) for line in (directory / "records.jsonl").read_text().splitlines()]
    if manifest.get("record_count") != len(rows) or manifest.get("records_digest") != digest(rows):
        raise ValueError("Dataset records do not match manifest.")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate sample IDs.")
    owners = {}
    for row in rows:
        validate_canonical(row)
        if row["split"] not in SPLITS or row["source_id"] != manifest["source_id"]:
            raise ValueError("Invalid sample split/source.")
        for key in (row["group_id"], (row["source_id"], row["building_id"]), geometry_key(row, 3)):
            if key in owners and owners[key] != row["split"]:
                raise ValueError("Cross-split leakage detected.")
            owners[key] = row["split"]
    return manifest, rows
