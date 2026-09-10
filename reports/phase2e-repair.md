# Phase 2E repair evaluation

**Date:** September 7, 2026

**Outcome:** the restricted repair component passes both the fixed 100-brief
benchmark and a fresh 1,000-brief stress run. The complete learned generator
still fails its five-concept/diversity release gates and remains offline.

## Experiment

The frozen Phase 2D model and a train-only mean-per-type reference feed the same
CP-SAT corridor-slot repair with the same solver budget, objectives and selection
rules. No model or repair setting was tuned against these benchmark results.
The [contract](../docs/CONSTRAINT_REPAIR.md) was committed before evaluation.
A shared-edge conversion defect found during stress testing was corrected with
strict tolerances, model weights and solver settings unchanged.

- Model state: `344a53149ef17be0a3b21e5284c4df742c27c59852629cbfbbc788d7a543f3c1`
- Training data: `e0efc4064fec21e0ca430ae356705052ba6002c70908fc3470606ddc944fd9aa`
- Benchmark: `7a545e2b28422980a8c60ffe888504300d2583a2de3aa36bdc29b7db9d7f9533`
- Frozen settings: ten repair attempts per brief, 0.03 deterministic work units per
  solve, adjacency reward 500 and minimum matched concept separation 0.025 diagonals.

## Fixed 100-brief comparison

| Metric | Heuristic | Frozen CP-SAT | Neural + repair | Reference + repair |
|---|---:|---:|---:|---:|
| Briefs with valid output | 100% | 100% | 100% | 100% |
| Returned layouts | 500 | 500 | 443 | 443 |
| Five-concept contract | 100% | 100% | 72% | 68% |
| At least four distinct under the new matching rule | Not measured | Not measured | 79% | 79% |
| Adjacency satisfaction | 65.54% | 99.39% | 99.48% | 99.62% |
| Original benchmark diversity score | 0.2386 | 0.1642 | 0.1699 | 0.1638 |
| Budget fit | 60.8% | 60.6% | 61.0% | 61.0% |
| Strict post-repair validity | Not measured | Not measured | 100% | 100% |

The heuristic, neural and reference summaries use fresh runs on the same briefs.
The CP-SAT column is the unchanged [Phase 2C report](phase2c-solver-comparison.md),
matched by benchmark digest; it is historical evidence, not a newly timed run.
All candidates also pass the original hard-compliance/program metrics. The new
repair validator is stricter and includes footprint coverage and actual doors.

Quality averages are calculated within each brief's returned set, then across
briefs. Missing concepts are counted separately and failed briefs remain in the
denominator. Returning fewer layouts does not establish an equally complete or
superior five-result generator.

## Repair effects and latency

Every raw neural benchmark proposal overlaps. All 443 selected repairs pass
strict room program, geometry, coverage, connected-door, entry/window and
compliance checks. No failed/unknown result or unvalidated fallback is returned.
All 1,000 repair attempts in each matched benchmark pipeline succeed before
selection removes duplicate and near-duplicate concepts.

Neural repair moves normalized box coordinates by 0.10742 on average, versus
0.19748 for reference repair. It has a four-percentage-point advantage in
five-concept completion but a 0.14-point adjacency disadvantage to the matched
reference. Its adjacency is 0.09 points above frozen CP-SAT. These mixed results
do not establish a learned quality advantage. Much of the usable geometry comes
from restricted corridor templates and deterministic constraints.

Observed warm CPU p95 is 0.970 seconds for neural repair and 1.026 seconds for
reference repair; neural maximum is 1.005 seconds. Neural checkpoint loading
is 0.981 seconds and is excluded from warm latency. Timing includes inference,
template generation, solves, validation and selection on one Python/PyTorch CPU
thread. It is not a hardware-independent SLA.

## Fresh 1,000-brief stress run

Seed 20260907 produces a fresh deterministic sample with digest
`b2864281d9242c79014efd51b16a1fbed69342da9adcdd3652e0d29fd5a3de47`.

| Metric | Result |
|---|---:|
| Briefs returning strict repair | 1,000/1,000 |
| Failed briefs / crashes | 0 / 0 |
| Validated returned layouts | 4,447 |
| Rejected template/repair attempts | 4 out of 10,000 |
| At least four distinct concepts | 81.3% |
| Five distinct concepts | 71.1% |
| Observed warm CPU p95 / maximum | 0.954 s / 1.073 s |

Four individual template/repair attempts are safely rejected, while every brief
still yields validated output. No-crash and repair-validity stress gates pass.
The complete-generator stress gate remains open because the five-result contract
fails for 28.9% of these briefs. The stress sample establishes supported synthetic
behavior, not real-plan generalization or architectural certification.

The [first stress run](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34091507351)
found 12 briefs with no returned plan. Independent room-edge rounding introduced
one-millimetre gaps/overlaps around half-millimetre boundaries. A standard-library
geometry replay reproduced the same 12 failures; the fix clusters only canonical
representation error and quantizes each shared edge once. A focused regression
test covers the formerly failing templates. Replaying all 1,000 briefs and then
the full model/solver pipeline closes the failure without weakening validation.

## Verification and retained evidence

The corrected implementation passes 68 backend tests at 94.06% coverage and
53 ML/repair tests at 98.62% coverage, with clean Ruff. Tests cover malformed
proposals, corrupted geometry, missing topology, solver failure, duplicate and
reflection matching, proposal influence, repeatability, checkpoint binding,
immutable reports, recorded failures and shared-edge quantization.

All seven jobs pass in the
[verified feature run](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34093445161),
including the complete stress run and exact reproduction of the Phase 2D tensor
digest. Full per-case results, stress cases and fixed-order raw/repair contact
sheets are in the
[comparison artifact](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34093445161/artifacts/10008163120).
Contact sheets were generated but have not been manually visually audited.

The [machine-readable record](phase2e-repair.json) stores exact environments,
metrics, gates, prior failure evidence and run links. CI artifacts have limited
retention; committed source, configuration and compact reports preserve reproduction.
Routine CI retains the full 100-brief regression; the full release stress run is
linked above and can be repeated using the documented `--stress-count 1000` command.

## Remaining release gates and next sprint

The +10-point adjacency and observed CPU latency gates pass. The existing
candidate promotion comparison fails because the five-result contract fails.
The new four-distinct gate also fails. The repair-component gate passing is not
full model-release qualification.

Phase 2F should prioritize diverse proposal/template generation under the same
strict repair boundary, using new development/validation briefs before tuning.
Evaluate neural contribution with identical repair settings for all controls,
then use a fresh locked holdout. Independent licensed real plans, blinded human
preference above 60%, and application/fallback integration remain required.
External Kaggle data remains unadmitted.
