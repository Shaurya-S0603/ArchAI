"""Prospectively seeded Phase 2F cohorts separated by model geometry inputs."""

import json
from pathlib import Path

from archai.datasets.schema import digest
from archai.evaluation.dataset import BenchmarkCase, build_synthetic_cases, dataset_digest
from archai.services.layout_generator import _room_specs, building_bounds_for_brief

ROOT = Path(__file__).resolve().parents[2]


def program_key(brief):
    bounds = building_bounds_for_brief(brief)
    return digest({"dimensions": sorted([bounds["width"], bounds["depth"]]),
                   "types": sorted(s.type for s in _room_specs(brief))})


def phase2f_cohorts():
    config = json.loads((ROOT / "ml/configs/phase2f-v1.json").read_text())
    seen = {program_key(c.brief) for count, seed in ((100, 20260903), (120, 20260905),
                                                   (1000, 20260907))
            for c in build_synthetic_cases(count, seed)}
    cohorts, manifest = {}, {"protocol": config, "excluded_programs": len(seen), "cohorts": {}}
    for name in ("development", "validation", "test", "stress"):
        rule, selected, rejected = config["cohorts"][name], [], 0
        for batch in range(20):
            for case in build_synthetic_cases(1000, rule["seed"] + batch * 100000):
                key = program_key(case.brief)
                if key in seen:
                    rejected += 1
                    continue
                seen.add(key)
                selected.append(BenchmarkCase(f"phase2f-{name}-{len(selected) + 1:04d}",
                                              "test" if name == "stress" else name, case.brief))
                if len(selected) == rule["count"]:
                    break
            if len(selected) == rule["count"]:
                break
        if len(selected) != rule["count"]:
            raise ValueError("Unable to fill unique Phase 2F cohort.")
        cohorts[name] = selected
        manifest["cohorts"][name] = {"count": len(selected), "sha256": dataset_digest(selected),
                                    "excluded_collisions": rejected}
    return cohorts, manifest
