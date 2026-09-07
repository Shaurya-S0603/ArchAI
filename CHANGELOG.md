# ArchAI changelog

Development milestones are listed newest first. Historical entries describe their
release-time scope; see [current status](docs/STATUS.md) for today's release gates.

## v0.2.0-dev.5 — Phase 2E constrained neural repair

Released September 7, 2026 on `development` for review.

- Add deterministic CP-SAT assignment of frozen neural proposals to corridor slots.
- Enforce room program, area, dimensions, bounds, zero overlap, footprint coverage,
  connected doors, entry and habitable-room windows on every returned plan.
- Rank and deduplicate up to five concepts, reporting shortfalls explicitly.
- Compare neural repair with a matched train-only reference and frozen generators.
- Record repair displacement, failures and CPU timing; the 1,000-brief stress
  run returns 4,447 validated layouts with zero crashes.
- Fix a shared-edge rounding defect found in 12 stress briefs without relaxing
  strict geometry tolerances or changing the frozen model/solver settings.
- Add 25 repair tests, immutable comparison artifacts and a seventh CI job.
- Consolidate five separate release-note files into this changelog, shorten repeated
  README/status material and remove temporary feature-branch CI entries.
- Exclude offline experiments and local artifacts from the production Docker context.
- Direct fresh benchmark outputs to ignored artifact directories; retain the frozen
  benchmark, source records, configurations and reports needed for reproduction.

On 100 fixed briefs, repair returns 443 strictly valid layouts with 99.48% adjacency
satisfaction. Four distinct concepts are available for 79% of briefs; five for 72%.
The matched reference scores 99.62% adjacency, so neural superiority is not established.
The repair component is complete; five-concept generation and product promotion
remain blocked. See [repair evidence](reports/phase2e-repair.md) and
[the contract](docs/CONSTRAINT_REPAIR.md). The web generator remains deterministic.

## v0.2.0-dev.4 — Phase 2D supervised graph baseline

This development increment adds ArchAI's first trained neural research model.
It establishes reproducible training and held-out evidence; overlap failures
keep the production application on the deterministic generator.

### Changes

- Add an optional CPU PyTorch package with four graph message-passing layers,
  bounded normalized room boxes and a symmetric adjacency head.
- Build program-only inputs with strict target separation and padding masks.
- Train using the admitted synthetic pilot, with validation-only checkpoint selection.
- Save immutable state-dict checkpoints, data/source/environment metadata and history.
- Verify checkpoints by hashes, vocabulary, configuration, dataset binding and finite weights.
- Add explicit split evaluation, a train-fitted reference, raw predictions and contact sheets.
- Add 28 ML tests and a sixth CI job, with an independent 90% ML coverage floor.

### Evidence

The frozen 120-epoch run uses 477 training and 55 validation plans and selects
epoch 96. On 60 test plans, normalized coordinate MAE is 0.105837 versus 0.211610
for the training-only reference, and adjacency F1 is 76.35% versus 72.37%.
The ML tests pass with 98.11% coverage. Full evidence, experiment dates and
artifact links are in [the report](reports/phase2d-baseline.md).

### Unmet gates

Every raw test proposal contains overlapping rooms. Constraint repair, connected
door/circulation topology, minimum dimensions, diverse valid candidates, CPU
p95, 1,000-brief stress behavior, human preference and real-plan generalization
remain unverified. External datasets remain quarantined. No new production
generator or reinforcement-learning system is included.

See [the reproduction guide](docs/LEARNED_BASELINE.md) and [model card](docs/MODEL_CARD.md).

## v0.2.0-dev.3 — Phase 2C data foundation

### Changes

- Add a strict rectangular-plan to canonical-room-graph adapter.
- Validate source reviews/checksums, geometry, room taxonomy and graph connectivity.
- Normalize bounded millimetre rounding, deduplicate geometry and keep transitive
  building/duplicate groups in the same train/validation/test split.
- Produce immutable datasets, provenance, rejection reports and visual QA sheets.
- Add explicitly split-selected, padded training batches without an ML framework.
- Add a fresh 592-plan synthetic pilot and a dedicated CI dataset regression gate.
- Fix the solver's load-sensitive wall-clock cutoff using a deterministic work
  budget, and record a fresh 100-case comparison without overwriting Phase 2B reports.

### Evidence

The pilot processes 600 plans from 120 fresh briefs, removes eight exact copies,
and retains 477 training / 55 validation / 60 test plans. All 13 supported room
types are present. The source and geometry exclusion checks keep the frozen
benchmark out of this pilot. See [dataset report](reports/phase2c-dataset.md).

The solver's 100-case comparison passes all existing promotion gates with its
new deterministic work limit. See [comparison](reports/phase2c-solver-comparison.md).

### Scope

The production generator remains the deterministic baseline. No neural training,
external-plan admission, source-specific Kaggle parser, model checkpoint or
real-world quality claim is included. See [pipeline contract](docs/TRAINING_DATA_PIPELINE.md)
for exact data scope, tolerances, exclusions and next steps.

Local release verification: 68 tests passing; 94.06% statement coverage; Ruff,
JavaScript syntax and whitespace checks clean. The 100-case solver comparison
and frozen pilot report gates pass. CI verifies the published development tree.

## ArchAI v0.2.0-dev.2

**Milestone:** Phase 2B - evaluated CP-SAT generator candidate

### Added

- optional OR-Tools 9.15 CP-SAT dependency and deterministic solver generator;
- named candidate registry and candidate-aware benchmark interface;
- baseline-versus-candidate JSON/Markdown comparison with enforced promotion gates;
- dedicated free-CPU GitHub Actions solver-comparison job;
- external dataset candidate register covering Kaggle discovery, original-source
  provenance, license compatibility, and checkpoint-redistribution review.

### Evaluation result

Across the frozen 100-case benchmark, `cp-sat-v1` returns five valid concepts for
every case and improves functional adjacency satisfaction from 65.54% to 98.41%.
It records 0.1745 diversity, 60.6% budget fit, 100% accessibility alignment, and
96.1% user alignment. Every predeclared Phase 2B promotion gate passes.

The solver is a research candidate, not the production API default. It does not
constitute a trained AI system, architectural certification, regulatory approval,
or evidence of real-world generalization.

### Reproduce

```bash
python -m pip install -r requirements-dev.txt
pytest --cov=archai --cov-fail-under=90
ruff format --check .
ruff check .
python -m archai.evaluation.comparison --enforce \
  --json reports/phase2b-comparison.json \
  --markdown reports/phase2b-comparison.md
```

## ArchAI v0.2.0-dev.1

**Milestone:** Phase 2A - evaluated generative-intelligence foundation

**Status:** Development preview

### Added

- a deterministic, versioned 100-case synthetic residential benchmark;
- fixed 60/20/20 development, validation, and test splits;
- manifest-level provenance, MIT license, exclusions, and SHA-256 integrity;
- generator-independent validity, program, adjacency, diversity, budget,
  accessibility, and user-alignment metrics;
- JSON and Markdown report generation through `python -m archai.evaluation`;
- enforceable regression thresholds and a dedicated GitHub Actions benchmark job;
- dataset-governance and candidate-promotion protocols.

### Baseline result

The Phase 1 deterministic generator passes all Phase 2A release gates across 100
briefs. Adjacency satisfaction is 65.54%, diversity is 0.2386, and budget fit is
60.8%. These become explicit Phase 2B improvement targets rather than hidden
assumptions.

### Compatibility

- The browser workflow and `/api/v1` routes remain compatible with v0.1.
- Project schema version remains 3.
- No paid service, GPU, external dataset, or new runtime dependency is required.

### Boundary

This release does not contain a trained model. Benchmark results compare generator
candidates and do not certify architectural quality, accessibility, structural
safety, building-code compliance, or construction readiness.

## ArchAI v0.1.0-dev.1

This is the first public development preview of the complete Phase 1 architectural
editor. It is intentionally published from the `development` branch for review
before promotion to `main`.

### Included

- five deterministic residential layout directions;
- constrained move, resize, keyboard, and exact numeric room editing;
- semantic corridors, walls, doors, entries, and windows;
- furniture-use, door-approach, and accessible turning zones;
- preliminary planning feedback and local parametric cost estimates;
- SQLite project save, load, update, delete, and schema upgrades;
- interactive 2D/3D previews;
- JSON, SVG, PNG, vector PDF, OBJ, and print output;
- Pytest, Playwright, axe-core, and GitHub Actions quality gates.

### Verification target

- Python tests with at least 90% statement coverage;
- clean Ruff and JavaScript syntax checks;
- Chromium end-to-end coverage for the primary editor workflow;
- no automated axe violations across WCAG 2.0, 2.1, and 2.2 A/AA rule sets.

### Development boundaries

This release is for concept exploration and software evaluation. It is not a
trained AI model, BIM authoring tool, permit drawing, accessibility certification,
or substitute for a qualified architect or engineer.
