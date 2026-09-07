# ArchAI Layout Generator Card

**Component:** ArchAI transparent baseline, CP-SAT candidate and supervised graph research model

**Version:** v0.2.0-dev.4

**Maintained by:** Shaurya Singhal

## Status

The production application uses the deterministic baseline. Two offline research
candidates are available: the CP-SAT solver and Phase 2D's trained supervised
graph regressor. The neural model has overlap failures on every held-out test
plan and is not approved for product integration. No reinforcement-learning
model is included.

## Purpose

- generate five residential concept layouts from a validated brief;
- represent room relationships as an adjacency graph;
- rank concepts using adjacency and compactness proxies;
- provide a no-GPU fallback for future learned generators.

## Inputs

- site width and depth;
- bedroom, bathroom, household, and optional-room counts;
- architectural style;
- budget and currency;
- sustainability and accessibility priorities.

## Outputs

- rectangular 2D room geometry in metres;
- building and site bounds;
- adjacency, compactness, and circulation-proxy metrics;
- corridor, wall, door, entry, and window topology;
- furniture-use, door-approach, and accessible turning zones;
- a concept ranking score.

## Method

The generator builds a room program from editable minimum and target areas,
reserves a continuous 1.8 m circulation spine, and allocates rooms as weighted
perimeter strips on both sides. It then derives atomic wall segments and selects
a connected spanning set of door openings. Exterior entry and window openings are
added from perimeter walls. A shared-wall graph is scored against functional
adjacency preferences. Furniture-use zones are then fitted within supported room
types, while door-approach zones follow semantic openings and accessible briefs
receive 1.5 m turning-circle overlays in bathrooms and circulation space.

The Phase 2B candidate uses CP-SAT to assign requested non-corridor rooms to
corridor sides and ordered slots. Hard solver constraints preserve unique slots,
minimum strip capacity, and occupied sides. Its objective rewards requested room
adjacency, area balance, and seeded concept variation. The assignment is then
passed through the same transparent rectangle, topology, zoning, and compliance
services as the baseline.

The Phase 2D model has 60,261 parameters, four message-passing layers and two
heads for normalized room boxes and symmetric shared-boundary adjacency labels.
Inputs contain room types, nominal/minimum areas, room instance/count features,
footprint dimensions and desired type-based edges. Observed boxes and edges are
supervision only. Training uses Adam and a fixed 120-epoch CPU configuration,
with checkpoint selection by validation loss. It produces one deterministic
raw proposal; bounds are enforced by parameterization, while non-overlap,
minimum area/dimensions and connected circulation are not guaranteed.
See [the exact model/training contract](LEARNED_BASELINE.md).

## Evaluation

The Phase 2A harness evaluates 100 fixed synthetic briefs. The baseline records
100% generation success, 100% five-concept contract adherence, 100%
hard-constraint passes, 100% room-program matches, 65.54% functional-adjacency
satisfaction, 0.2386 normalized concept diversity, 60.8% budget fit, and 100%
accessibility alignment. The dataset digest and case-level results are included
in the machine-readable report.

On the identical 100-case digest, the CP-SAT candidate records 100% generation,
five-concept, hard-constraint, and room-program passes; 98.41% adjacency
satisfaction; 0.1745 diversity; 60.6% budget fit; 100% accessibility alignment;
and 96.1% user alignment. All predeclared Phase 2B comparison gates pass.

These are candidate-comparison metrics on supported synthetic inputs. They do
not establish architectural quality, real-world generalization, regulatory
compliance, accessibility certification, or structural safety.

On the independent Phase 2C pilot split (60 test plans, 735 rooms), the selected
neural checkpoint achieves normalized coordinate MAE 0.105837, compared with
0.211610 for a mean-per-room-type reference fitted on training data. Adjacency
F1 is 76.35% versus 72.37%. Mean room IoU is only 0.096222, and all 60 neural
outputs overlap. The combined raw geometry pass rate is 0%. Validation has
minimum-area failures as well. This is not a comparison against the heuristic or
solver, and adjacency F1 does not measure a connected door graph.
See [the experiment and failures](../reports/phase2d-baseline.md).

## Data

Phase 2D trains on the Phase 2C 592-plan synthetic pilot: 477 training,
55 validation and 60 test plans, grouped by building and geometry duplicates.
The fixed configuration was selected before test evaluation; epoch 96 was
selected using validation loss. Test data was not used in training or selection.
The pilot inherits the deterministic teacher's corridor/perimeter bias and is
not a real-plan corpus. See [the data contract](TRAINING_DATA_PIPELINE.md).

The committed evaluation inputs are synthetic
briefs generated by ArchAI code and contain no external floor plans. CubiCasa5K,
FloorCAD, or any other dataset must
undergo license, provenance, bias, and split review before entering a trained
model or distributed checkpoint. Kaggle candidates are recorded in
`docs/DATASET_CANDIDATES.md`; none is admitted in this release.

## Limitations

- single-floor rectangular residential concepts only;
- doors and windows are concept geometry, not detailed construction assemblies;
- concept zones are not product-specific furniture layouts or accessibility certification;
- no structural system or building-services coordination;
- generated geometry may require substantial professional revision;
- the score is a transparent heuristic, not confidence or design approval;
- regional, cultural, climatic, and site-specific requirements are not modeled.
- raw learned boxes overlap; squared-error regression can average multiple teacher arrangements;
- desired-graph conditioning is trained only on default type-based requests;
- arbitrary input graphs, stochastic diversity and independent real-plan performance are unvalidated.

## Reproducibility and artifacts

The frozen model uses PyTorch 2.10.0+cpu, one CPU thread, deterministic algorithms,
and seed 20260906. Run metadata records Python/platform versions, code/data hashes,
configuration, validation history and tensor-state digest. Checkpoints use CPU
state-dict loading with `weights_only=True` and integrity checks. Same-environment
repeat training is tested; cross-version or cross-platform identity is not promised.
The complete experiment is an expiring CI artifact, while source/configuration
and compact reports are committed for reproduction. No dataset or large checkpoint
is committed and the web-only install has no PyTorch dependency.

## Model promotion gate

The 0.1-second CP-SAT cutoff varied under CPU load. Phase 2C replaces it with
`max_deterministic_time=0.1`, one worker and fixed seeds. This supports repeatability
in the pinned OR-Tools environment; it is not a wall-clock latency guarantee.
The new comparison is in `reports/phase2c-solver-comparison.md`; historical reports
are unchanged. See [OR-Tools limit definitions](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto).

A trained generator will be released only with a reproducible training pipeline,
held-out evaluation data, comparison against this frozen baseline, documented
failure cases, and hard-constraint checks that remain outside the learned model.
The public synthetic test split is not sufficient evidence of real-world
generalization on its own.
