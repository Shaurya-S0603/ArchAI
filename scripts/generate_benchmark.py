"""Regenerate the committed Phase 2A synthetic benchmark."""

import sys
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

write_benchmark = import_module("archai.evaluation.dataset").write_benchmark


if __name__ == "__main__":
    destination = Path("data/benchmarks/v1")
    manifest = write_benchmark(destination)
    print(f"Wrote {manifest['case_count']} cases to {destination} (sha256={manifest['sha256']}).")
