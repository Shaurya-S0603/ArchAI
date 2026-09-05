# v0.2.0-dev.3 — Phase 2C data foundation

## Changes

- Add a strict rectangular-plan to canonical-room-graph adapter.
- Validate source reviews/checksums, geometry, room taxonomy and graph connectivity.
- Normalize bounded millimetre rounding, deduplicate geometry and keep transitive
  building/duplicate groups in the same train/validation/test split.
- Produce immutable datasets, provenance, rejection reports and visual QA sheets.
- Add explicitly split-selected, padded training batches without an ML framework.
- Add a fresh 592-plan synthetic pilot and a dedicated CI dataset regression gate.
- Fix the solver's load-sensitive wall-clock cutoff using a deterministic work
  budget, and record a fresh 100-case comparison without overwriting Phase 2B reports.

## Evidence

The pilot processes 600 plans from 120 fresh briefs, removes eight exact copies,
and retains 477 training / 55 validation / 60 test plans. All 13 supported room
types are present. The source and geometry exclusion checks keep the frozen
benchmark out of this pilot. See [dataset report](../reports/phase2c-dataset.md).

The solver's 100-case comparison passes all existing promotion gates with its
new deterministic work limit. See [comparison](../reports/phase2c-solver-comparison.md).

## Scope

The production generator remains the deterministic baseline. No neural training,
external-plan admission, source-specific Kaggle parser, model checkpoint or
real-world quality claim is included. See [pipeline contract](TRAINING_DATA_PIPELINE.md)
for exact data scope, tolerances, exclusions and next steps.

Local release verification: 68 tests passing; 94.06% statement coverage; Ruff,
JavaScript syntax and whitespace checks clean. The 100-case solver comparison
and frozen pilot report gates pass. CI verifies the published development tree.
