# ArchAI - Project Status

**Last updated:** September 5, 2026

**Release branch:** `development` (Phase 2 review into `main`)

**Current milestone:** Phase 2C data foundation - v0.2.0-dev.3

## Overall status

ArchAI now supports local project persistence, constrained room resizing, semantic
plan topology, deterministic furniture/accessibility zones, printable plan
output, a versioned generator benchmark, and an optional CP-SAT research
candidate while retaining the Python, Flask, HTML, CSS, and JavaScript stack.
The development preview provides evaluated baseline and solver candidates, not the complete trained AI,
BIM, code-certification, or VR product described in the research plan.

**Project health:** Phase 2C data interface implemented; learned generation remains research work.

## Implemented

- Flask application factory, production WSGI entrypoint, and versioned JSON API;
- validated residential design survey;
- five deterministic corridor/perimeter layout concepts;
- room adjacency graph and ranking metrics;
- generic preliminary rule checks with clear professional-review boundaries;
- parametric local cost baseline and budget comparison;
- editable SVG plan with pointer/keyboard movement and undo/redo;
- interactive browser 3D massing preview;
- JSON, SVG, PNG, vector PDF, and OBJ exports plus browser printing;
- Windows and Unix launchers, Dockerfile, and free Render blueprint;
- automated Python tests and lint configuration;
- architecture, traceability, roadmap, and corrected model documentation.

## Phase 1A implemented

- SQLite project store with a forward-only migration ledger;
- save, list, load, update, and delete project API routes;
- server-side schema validation plus compliance and cost recomputation on save;
- browser project library with accessible status feedback;
- four corner resize handles with grid snapping, footprint bounds, minimum room
  dimensions, and room-type minimum areas;
- undo/redo support for move and resize operations.

## Phase 1B implemented

- one continuous 1.8 m corridor spine in every generated concept;
- perimeter room strips that preserve minimum dimensions and corridor access;
- deterministic deduplicated exterior, interior, and exposed-boundary walls;
- a connected spanning set of interior doors plus one exterior entry door;
- exterior windows for every generated habitable room;
- automatic wall/opening rebuilding after geometry edits;
- topology-aware compliance and accessibility door-width feedback;
- semantic topology in JSON persistence and SVG exports;
- automatic schema v1 to schema v2 project upgrades on load.

## Phase 1C implemented

- deterministic furniture-use zones for supported room types;
- door-approach clearances derived from semantic openings;
- 1.5 m turning-circle overlays for accessible bathrooms and circulation space;
- automatic zoning rebuilding after generation, editing, analysis, save, and load;
- schema v3 project snapshots with automatic upgrades from schemas v1 and v2;
- browser-native PNG downloads and print-specific page styling;
- vector A3 landscape PDF plan sheets with title block, scale, north arrow,
  planning checks, and a professional-review disclaimer;
- free, local PDF generation with the BSD-licensed ReportLab toolkit.

## Phase 1D quality gate implemented

- exact numeric room editing as a no-drag alternative;
- keyboard-operated concept tabs, room selection, movement, focus treatment, and
  skip navigation;
- minimum interactive target sizing and focus-obscuring safeguards;
- serial Playwright coverage for generation, editing, undo, 3D switching,
  persistence, reload, and PDF export;
- automated axe checks for WCAG 2.0, 2.1, and 2.2 A/AA rules in initial and
  generated interface states;
- GitHub Actions jobs for Python quality and Chromium browser quality.

## Phase 2A implemented

- 100 deterministic synthetic briefs with fixed development, validation, and
  test splits;
- versioned JSONL contract plus manifest provenance, license, exclusions, seed,
  and SHA-256 integrity;
- independent metrics for generation success, hard constraints, program match,
  functional adjacency, diversity, budget, accessibility, and user alignment;
- JSON and Markdown report outputs plus non-zero regression-gate failures;
- committed deterministic-baseline report and documented evaluation protocol;
- dedicated GitHub Actions benchmark job using only free local resources.

## Phase 2B implemented

- optional OR-Tools CP-SAT generator, isolated from the default runtime;
- deterministic room-side and position assignment with five seeded objectives;
- existing geometry construction, semantic topology, zoning, and hard validation
  reused after solver assignment;
- candidate registry, candidate-aware benchmark CLI, comparison CLI, and
  machine-readable promotion gates;
- committed 100-case comparison showing 98.41% adjacency satisfaction, 0.1745
  diversity, and no material budget or user-alignment regression;
- documented Kaggle shortlist with external data kept quarantined pending exact
  license, provenance, privacy, derivative, and checkpoint-distribution review;
- dedicated GitHub Actions solver-comparison job using free CPU resources.

## Verification

- Python unit/integration tests cover the
  editor, evaluation pipeline, candidate registry, and comparison CLI;
- Python lint clean;
- all JavaScript modules pass syntax checks;
- Flask development and Gunicorn production entrypoints respond successfully.
- the 100-case baseline passes every enforced regression gate;
- the 100-case CP-SAT comparison passes every Phase 2B promotion gate;
- browser tests and accessibility checks run locally and in CI.

## Next milestone

Phase 2D implements the supervised graph-conditioned baseline using admitted
synthetic data. External sources remain blocked pending review.
See `docs/TRAINING_DATA_PIPELINE.md` for Phase 2C's contract and reproduction.
Independent real-plan validation, constraint repair and release-scale
stress/performance checks are still open.

## Phase 2C implemented

- separate room-graph schema v1; metre units, 4-32 rectangular rooms, explicit
  taxonomy and minimum-area/overlap/boundary/connectivity validation;
- bounded 2 mm edge snapping to normalize millimetre rounding;
- source checksums and training/derivative/redistribution/privacy review records;
- exact and coarse geometry duplicate buckets, with transitive building groups;
- 120-brief pilot: 600 input plans, 8 duplicates removed, 592 accepted;
  477 train / 55 validation / 60 test across all 13 room types;
- exclusion of all 100 benchmark briefs and matching baseline geometry groups;
- immutable artifacts, canonical revalidation, padded batches and visual QA;
- deterministic solver work limit replacing the flaky 0.1-second cutoff;
- dedicated CI pilot regression gate and dataset report artifacts.

Local release verification: 68 tests passing; 94.06% statement coverage; Ruff,
JavaScript syntax and whitespace checks clean. The 100-case solver comparison
and frozen pilot report gates pass. CI verifies the published development tree.
