# Phase 2E constrained neural proposals

Phase 2E projects the frozen Phase 2D proposal into ArchAI's existing rectangular
corridor/perimeter family. Its purpose is to close raw geometry failures and
measure the repaired generator, including whether the neural model adds value.
The production API remains on its existing deterministic generator.

## Contract frozen before the comparison

The model and training-data digests must match `reports/phase2d-baseline.json`.
No retraining or hyperparameter selection uses the repair benchmark. Replaying
the Phase 2D training configuration in CI produces the checkpoint consumed by
the repair job, which verifies the frozen identities before evaluation.

Input proposals list the exact requested room types in canonical type/instance
order, with one normalized `[x, y, width, depth]` box each. Finite coordinate
magnitudes up to two are supported, including out-of-bound positions; widths and
depths must be positive. Unknown fields, wrong room programs, NaNs and invalid
sizes are rejected. There are no observed boxes or edges in neural inputs.

Five layouts from the unchanged deterministic generator define feasible slot
templates. Shared endpoints are normalized and put on a common millimetre grid. Canonical
start/size rounding error is clustered within 2e-8 normalized units before each
shared edge is quantized once; independently rounding each room can introduce
one-millimetre gaps at half-millimetre ties.
For each template, CP-SAT assigns each room to exactly one slot and each slot to
exactly one room. The corridor retains its slot. Assignment choices violating
1.8 m minimum dimensions or room-type minimum areas are forbidden.

The objective is the sum of normalized coordinate L1 displacements, rounded to
integer thousandths, minus 500 times weighted preferred adjacency. Five existing
functional objectives are used over two passes (ten solves). The work budget
is 0.03 deterministic units per solve, one worker and fixed solver seeds.
Template assignments supply feasible hints. Only FEASIBLE/OPTIMAL solver results
are accepted; UNKNOWN is an explicit failure, not proof of infeasibility.
[CP-SAT integer constraints and statuses](https://developers.google.com/optimization/cp/cp_solver),
[deterministic limit definition](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto).

This is a restricted assignment projection over fixed slots. It does not move
walls freely or establish the closest possible feasible layout across all floor
plans. A large repair displacement can mean the rules dominate the proposal.
Returned diagnostics expose displacement, solver status, objective and bound.
No unvalidated fallback is substituted when repair fails.

## Validation and selection

Every accepted layout is independently checked for exact room program, unique
IDs, correct footprint, finite coordinates, minimum area/dimensions, boundary
containment, overlap and full footprint coverage. Overlap tolerance is one square
millimetre per room pair. Area minima allow 1e-6 square metres numerical error;
boundary tolerance is 1e-6 metres; footprint coverage tolerance is 1e-4 square metres.
These checks are stricter than the web editor's preliminary compliance tolerances.

Topology and zoning are rebuilt from repaired geometry. The validator requires
an entry, every room reachable through actual generated doors, exterior windows
for all supported habitable types, and no compliance errors. These are concept
checks; local building-code certification and structural design are outside scope.

Feasible repairs are ranked by independently measured functional adjacency,
then displacement, then geometry fingerprint. Exact/coarse duplicate geometry
and global reflections are removed. Repeated room types are matched optimally
when measuring center displacement; renaming identical room types cannot inflate
diversity. Selected concepts must differ by at least 0.025 footprint diagonals
in mean matched room-center distance (after considering whole-plan reflections).
Up to five are returned. Shortfalls are reported; copies do not pad the result.

## Reproduce

Install the existing application/solver and optional CPU ML requirements, then
reproduce Phase 2D using `docs/LEARNED_BASELINE.md`. After obtaining its frozen run:

```bash
pytest tests/test_ml.py tests/test_repair.py --cov=archai_ml --cov-fail-under=90
python -m archai_ml.repair_evaluation --run ml/runs/phase2d-v1 \
  --output repair-artifacts/comparison-v1 --config ml/configs/phase2e-v1.json --enforce
```

The default comparison uses all 100 frozen generator benchmark briefs. It
compares neural-plus-repair with a matched train-only type-reference-plus-repair
pipeline and a fresh deterministic baseline. The unchanged solver's frozen
Phase 2C report is included only when its benchmark digest matches; it is labeled
historical rather than a fresh timed run. Original benchmark reports are retained.

The CLI writes an immutable report, per-case failures and timings, displacement
evidence, examples and a raw/repair contact sheet. Failed briefs remain in the
denominator. Runtime measures model inference, templates, all solves, validation
and selection; checkpoint loading is reported separately. Observed CPU latency
on a CI machine is not a hardware-independent SLA.

To run an additional repair-pipeline stress sample on fresh deterministic briefs:

```bash
python -m archai_ml.repair_evaluation --run ml/runs/phase2d-v1 \
  --output repair-artifacts/stress-v1 --config ml/configs/phase2e-v1.json \
  --stress-count 1000 --enforce
```

## Separate gates

`--enforce` requires every supported benchmark brief to return at least one
strictly valid repaired plan with the exact room program. This is the Phase 2E
repair-component gate, not the complete five-concept model-release gate. When
`--stress-count` is supplied, every stress brief must also return a strictly valid
repair. Stress case records and separate five-concept stress gates are retained.
Routine CI runs the full 100-brief comparison; the release stress run uses 1,000
fresh briefs and is linked from the committed report.

Generator quality is reported separately against the unchanged comparison gates,
including a ten-percentage-point adjacency gain over the heuristic, at least four
distinct concepts, the five-result contract, and observed CPU p95 below five
seconds. The matched reference comparison tests whether neural conditioning helps
after repair. A valid repaired output alone does not prove that benefit.

Full release still needs independent licensed real-plan validation, blinded human
preference above 60%, complete-generator stress evidence and application/fallback
integration. Any failed diversity or generator-quality gate remains a blocker.
No external data is admitted by this increment.

See [the Phase 2E results](../reports/phase2e-repair.md) for measured outcomes and
explicit unmet generator gates.
