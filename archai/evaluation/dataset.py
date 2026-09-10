"""Versioned synthetic benchmark data for generator evaluation.

The fixture briefs contain no copied floor plans or personal data. They are
created deterministically from the public ArchAI input ranges and are committed
so every generator candidate is measured against the same cases.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from random import Random
from typing import Any

from archai.models import ALLOWED_STYLES, DesignBrief
from archai.services.cost_estimator import CURRENCY_FROM_SGD, STYLE_RATE_SGD_M2

BENCHMARK_NAME = "archai-synthetic-residential-v1"
BENCHMARK_SCHEMA_VERSION = 1
DEFAULT_SEED = 20_260_903
DEFAULT_CASE_COUNT = 100
SPLITS = ("development", "validation", "test")
OTHER_ROOM_TYPES = ("study", "garage", "laundry", "balcony", "lounge", "storage", "utility")


@dataclass(frozen=True)
class BenchmarkCase:
    """One immutable benchmark input and its fixed evaluation split."""

    id: str
    split: str
    brief: DesignBrief

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": BENCHMARK_SCHEMA_VERSION,
            "id": self.id,
            "split": self.split,
            "brief": self.brief.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkCase:
        if not isinstance(data, dict):
            raise ValueError("Each benchmark case must be a JSON object.")
        if data.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
            raise ValueError(f"Benchmark cases must use schema version {BENCHMARK_SCHEMA_VERSION}.")
        case_id = str(data.get("id", "")).strip()
        if not case_id:
            raise ValueError("Each benchmark case requires an id.")
        split = str(data.get("split", "")).strip()
        if split not in SPLITS:
            raise ValueError(f"Benchmark split must be one of: {', '.join(SPLITS)}.")
        return cls(id=case_id, split=split, brief=DesignBrief.from_dict(data.get("brief", {})))


def _split_for_index(index: int, count: int) -> str:
    development_end = round(count * 0.60)
    validation_end = development_end + round(count * 0.20)
    if index < development_end:
        return "development"
    if index < validation_end:
        return "validation"
    return "test"


def _site_dimensions(rng: Random, non_corridor_rooms: int, rotate: bool) -> tuple[float, float]:
    # The current baseline places rooms in two perimeter strips. This lower bound
    # keeps every benchmark brief feasible without using generator output to
    # select or reject cases.
    rooms_on_busy_side = ceil(non_corridor_rooms / 2) + 2
    minimum_short_side = ceil(rooms_on_busy_side * 1.8 / 0.84)
    short_side = float(max(14, minimum_short_side) + rng.randint(0, 8))
    long_side = float(min(60, int(short_side) + rng.randint(4, 20)))
    if rotate:
        return long_side, short_side
    return short_side, min(80.0, long_side + rng.randint(0, 12))


def _budget_for_brief(
    site_width_m: float,
    site_depth_m: float,
    style: str,
    currency: str,
    room_count: int,
    sustainability: bool,
    ratio: float,
) -> float:
    footprint_area = site_width_m * site_depth_m * 0.84 * 0.84
    complexity = 1.0 + max(0, room_count - 8) * 0.012
    sustainability_factor = 1.06 if sustainability else 1.0
    estimated = (
        footprint_area
        * STYLE_RATE_SGD_M2[style]
        * complexity
        * sustainability_factor
        * CURRENCY_FROM_SGD[currency]
    )
    rounding = 10_000 if currency == "INR" else 1_000
    return float(round(estimated * ratio / rounding) * rounding)


def build_synthetic_cases(
    count: int = DEFAULT_CASE_COUNT,
    seed: int = DEFAULT_SEED,
) -> list[BenchmarkCase]:
    """Build deterministic, license-clean benchmark inputs."""

    if not 1 <= count <= 1_000:
        raise ValueError("Benchmark case count must be between 1 and 1,000.")

    rng = Random(seed)
    styles = tuple(sorted(ALLOWED_STYLES))
    currencies = tuple(CURRENCY_FROM_SGD)
    budget_ratios = (0.90, 1.00, 1.10, 1.25)
    cases: list[BenchmarkCase] = []

    for index in range(count):
        bedrooms = index % 6 + 1
        bathrooms = index * 3 % 5 + 1
        optional_count = index % 4
        other_rooms = tuple(sorted(rng.sample(OTHER_ROOM_TYPES, optional_count)))
        style = styles[index % len(styles)]
        currency = currencies[index // len(styles) % len(currencies)]
        sustainability = index % 3 == 0
        accessibility = index % 4 == 0
        non_corridor_rooms = 3 + bedrooms + bathrooms + len(other_rooms)
        site_width_m, site_depth_m = _site_dimensions(
            rng,
            non_corridor_rooms,
            rotate=index % 2 == 1,
        )
        household_size = min(12, max(1, bedrooms + 1 + index % 4))
        room_count = non_corridor_rooms + 1
        budget = _budget_for_brief(
            site_width_m,
            site_depth_m,
            style,
            currency,
            room_count,
            sustainability,
            budget_ratios[index % len(budget_ratios)],
        )
        brief = DesignBrief.from_dict(
            {
                "site_width_m": site_width_m,
                "site_depth_m": site_depth_m,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "style": style,
                "budget": budget,
                "currency": currency,
                "household_size": household_size,
                "other_rooms": list(other_rooms),
                "sustainability": sustainability,
                "accessibility": accessibility,
            }
        )
        cases.append(
            BenchmarkCase(
                id=f"synthetic-v1-{index + 1:04d}",
                split=_split_for_index(index, count),
                brief=brief,
            )
        )
    return cases


def serialize_cases(cases: list[BenchmarkCase]) -> str:
    return "".join(
        f"{json.dumps(case.to_dict(), sort_keys=True, separators=(',', ':'))}\n" for case in cases
    )


def dataset_digest(cases: list[BenchmarkCase]) -> str:
    return hashlib.sha256(serialize_cases(cases).encode("utf-8")).hexdigest()


def benchmark_manifest(cases: list[BenchmarkCase], seed: int = DEFAULT_SEED) -> dict[str, Any]:
    split_counts = {split: sum(case.split == split for case in cases) for split in SPLITS}
    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "name": BENCHMARK_NAME,
        "case_count": len(cases),
        "seed": seed,
        "sha256": dataset_digest(cases),
        "splits": split_counts,
        "license": "MIT",
        "provenance": (
            "Deterministically generated from ArchAI's documented input ranges; "
            "contains no external plans or personal data."
        ),
        "intended_use": "Regression evaluation and candidate-generator comparison.",
        "excluded_uses": [
            "Building-code certification",
            "Structural validation",
            "Training-data quality claims",
            "Real-world demographic representation claims",
        ],
    }


def write_benchmark(directory: Path, count: int = DEFAULT_CASE_COUNT) -> dict[str, Any]:
    cases = build_synthetic_cases(count=count)
    manifest = benchmark_manifest(cases)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "briefs.jsonl").write_text(serialize_cases(cases), encoding="utf-8")
    (directory / "manifest.json").write_text(
        f"{json.dumps(manifest, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    return manifest


def load_benchmark(path: Path) -> tuple[dict[str, Any], list[BenchmarkCase]]:
    directory = path if path.is_dir() else path.parent
    cases_path = directory / "briefs.jsonl" if path.is_dir() else path
    manifest_path = directory / "manifest.json"
    if not cases_path.is_file() or not manifest_path.is_file():
        raise ValueError("Benchmark requires manifest.json and briefs.jsonl.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Benchmark files must contain valid UTF-8 JSON.") from exc

    cases = [BenchmarkCase.from_dict(row) for row in rows]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Benchmark case ids must be unique.")
    if manifest.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
        raise ValueError("Benchmark manifest schema version is unsupported.")
    if manifest.get("case_count") != len(cases):
        raise ValueError("Benchmark manifest case_count does not match briefs.jsonl.")
    if manifest.get("sha256") != dataset_digest(cases):
        raise ValueError("Benchmark digest does not match briefs.jsonl.")
    return manifest, cases
