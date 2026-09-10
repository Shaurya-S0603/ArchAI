"""Fresh synthetic pilot; frozen evaluation briefs are never used as training rows."""

from __future__ import annotations

import hashlib
from pathlib import Path

from archai.datasets.pipeline import preprocess, write_dataset
from archai.datasets.schema import canonicalize, digest, encode, geometry_key
from archai.evaluation.dataset import DEFAULT_SEED, build_synthetic_cases, load_benchmark
from archai.services.layout_generator import generate_layouts

PILOT_SEED = 20260905
PILOT_SOURCE = "archai-synthetic-roomgraphs-v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def layout_record(layout, record_id: str, building_id: str, source_id: str) -> dict:
    """Explicit adapter for generator outputs; does not read saved user projects."""
    return {
        "schema_version": 1,
        "id": record_id,
        "building_id": building_id,
        "source_id": source_id,
        "units": "m",
        "footprint": dict(layout.building_bounds),
        "rooms": [
            {
                "id": room.id,
                "type": room.type,
                "box": {k: getattr(room, k) for k in ("x", "y", "width", "depth")},
            }
            for room in layout.rooms
        ],
    }


def evaluation_exclusions(directory: Path) -> tuple[set[str], set[str]]:
    _, cases = load_benchmark(directory)
    keys = set()
    for case in cases:
        for layout in generate_layouts(case.brief):
            row = canonicalize(layout_record(layout, layout.id, case.id, "evaluation"))
            keys.add(geometry_key(row, 3))
    return {digest(c.brief.to_dict()) for c in cases}, keys


def synthetic_source(payload: bytes) -> dict:
    return {
        "schema_version": 1,
        "id": PILOT_SOURCE,
        "version": "1",
        "origin": "synthetic",
        "license": "MIT",
        "source_url": "https://github.com/Shaurya-S0603/ArchAI",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "review": {
            "training": True,
            "derivatives": True,
            "redistribution": True,
            "checkpoint_distribution": True,
            "privacy": True,
            "reviewer": "ArchAI synthetic pipeline policy",
            "date": "2026-09-05",
            "evidence": "Repository LICENSE; generated solely from ArchAI code and "
            "fresh briefs; no external plans or saved user projects.",
        },
        "coverage": "Single-floor rectangular synthetic residential plans; all supported types.",
        "limitations": "Deterministic corridor/perimeter teacher bias; no real-plan quality "
        "or learned-generator improvement claim.",
    }


def build_pilot(
    destination: Path, count: int = 120, seed: int = PILOT_SEED, benchmark: Path | None = None
) -> dict:
    if seed == DEFAULT_SEED:
        raise ValueError("The frozen evaluation seed cannot generate training data.")
    excluded_briefs, excluded_keys = evaluation_exclusions(
        benchmark or PROJECT_ROOT / "data/benchmarks/v1"
    )
    raw = []
    for case in build_synthetic_cases(count=count, seed=seed):
        brief_key = digest(case.brief.to_dict())
        if brief_key in excluded_briefs:
            continue
        for i, layout in enumerate(generate_layouts(case.brief)):
            raw.append(
                layout_record(
                    layout, f"pilot-{seed}-{case.id}-{i}", f"brief-{brief_key}", PILOT_SOURCE
                )
            )
    payload = ("".join(encode(row) + "\n" for row in raw)).encode()
    source = synthetic_source(payload)
    rows, report = preprocess(payload, source, seed=seed, excluded_keys=excluded_keys)
    report["pilot"] = {
        "requested_briefs": count,
        "seed": seed,
        "excluded_briefs": count - len(raw) // 5,
        "evaluation_brief_keys": len(excluded_briefs),
        "teacher": "deterministic-baseline",
    }
    write_dataset(destination, rows, report, source, seed=seed)
    return report
