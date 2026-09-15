# ArchAI Layout Generator Card

**Component:** ArchAI transparent baseline, CP-SAT candidate and supervised graph research model

**Version:** v0.2.0-alpha.2

**Maintained by:** Shaurya Singhal

## Status

The default application uses the deterministic baseline. The CP-SAT solver remains
an offline comparator. Phase 2F adds an operator-enabled experimental engine using
the frozen supervised graph model, strict repair and bounded diversity search.
Invalid or unavailable experimental output triggers an identified deterministic
fallback. Raw neural proposals are never served. Neural superiority, independent
real-plan evaluation and human preference remain unqualified. No reinforcement
learning or learned ranking model is included.

Phase 2G adds an offline concept-conditioned model and three-seed controlled
experiment. Its raw prediction improvement does not pass the downstream benefit
gate; these checkpoints are incompatible with the existing serving loader.

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

## Phase 2E repair evidence

The frozen model supplies room boxes to a CP-SAT assignment over fixed corridor
slots. Program, dimensions, areas, boundary, overlap, coverage and actual door
connectivity are checked independently after geometry is built. At most five
valid concepts are returned after type-matched duplicate/reflection rejection.
This is a restricted projection, not arbitrary wall/box optimization.

On the 100-brief generator benchmark, all briefs return valid repair: 443 layouts,
99.48% adjacency, 0.1699 diversity and 61.0% budget fit. Four distinct concepts are
returned for 79% of briefs and five for 72%. The train-only reference with identical
repair settings reaches 99.62% adjacency and 68% five-concept completion. Neural
repair changes normalized coordinates by 0.10742 on average; substantial repair
means the solver can dominate proposal geometry. All raw benchmark proposals overlap.

The observed warm CPU p95 is 0.970 seconds, excluding the separately
reported 0.981-second checkpoint load. Timings describe the CI machine, not every
CPU or deployment. The fixed Phase 2C CP-SAT report records 99.39% adjacency on
this benchmark; it is a historical comparison, not a fresh timing measurement.
See [repair evidence and stress results](../reports/phase2e-repair.md) and
[the exact contract](CONSTRAINT_REPAIR.md). All 1,000 fresh stress briefs return strict repair (4,447 layouts, zero crashes),
but Phase 2E returned five concepts for only 71.1%. Phase 2F addresses this shortfall
with fresh qualification under the [new protocol](PHASE2F_PROTOCOL.md).

## Phase 2F method and serving

The model and CP-SAT repair settings remain frozen. On shortfall, the search moves
the corridor within an interval constrained by every room's minimum area and
width, rebuilding both perimeter strips on shared millimetre edges. A bounded
compatible-set search selects five plans under the unchanged 0.025 separation
threshold, repeated-type matching and reflection rejection. This expands room
proportions within one layout family; it does not establish new topology diversity.

A trusted local checkpoint is checksum- and identity-verified once per worker.
Inference is serialized, stores no request history and validates all five outputs
at the serving boundary. The API reports the selected engine and any fallback.
Warm single-request timing excludes worker queueing, checkpoint load and HTTP
transport. Cost model `gross-footprint-v2` charges the complete building footprint;
historical budget results used room-area sums and must not be mixed with new ones.
See [qualification and reproduction](PHASE2F_PROTOCOL.md).

Fresh Phase 2F development/validation (32/32), release holdout (100) and stress
(1,000) cohorts all return five strictly valid distinct concepts per brief.
Holdout adjacency is 99.14% versus baseline 65.36% and matched reference 99.67%.
Stress returns 5,000 valid plans, zero failed briefs/crashes and 0.785 s warm p95;
holdout p95 is 0.799 s. The learned pipeline's benchmark diversity is 0.1666 versus
0.1530 for the matched reference, but overall neural superiority remains unproven.
See [full qualification evidence](../reports/phase2f-qualification.md).

## Phase 2G research evidence

Both experimental arms have 60,581 parameters and add the same five-token
embedding to the graph representation. The conditioned arm receives a selected
teacher-control token; the ablation always receives token zero. Identical
initialization, minibatches and budgets isolate this intervention. Checkpoints
are selected by validation loss across 120 epochs for each of three fixed seeds.

Fresh synthetic cohorts contain 592 training, 158 validation and 493 reserved
test targets, with prior programs and duplicate groups excluded. Test targets are
not scored. On the same 32 validation briefs, conditioning reduces raw coordinate
MAE by 35.89–36.55% and improves repaired diversity by 31.42–35.14% against token
ablation. All 158 raw neural validation outputs still overlap for every seed.

All four compared arms return five strictly valid, distinct plans per brief.
Conditioned adjacency is 98.98–99.13%, compared with 100% for the train-only
concept/type reference and 99.89% for the solver-only control. Both cheap controls
also have higher diversity. No seed passes the overall neural-benefit gate.
Warm p95 is 0.818–1.075 seconds for the conditioned pipeline on the measured
runners. These are validation results within one teacher family, not independent
architectural quality evidence. The Phase 2F serving checkpoint remains frozen.
See [all results and failures](../reports/phase2g-conditioning.md) and
[the prospective protocol](PHASE2G_PROTOCOL.md).

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
- budget fit is a check on the fixed building footprint and requested program;
  rearranging interior partitions cannot reduce its quoted construction area;
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
