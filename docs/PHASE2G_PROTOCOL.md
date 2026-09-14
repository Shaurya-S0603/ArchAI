# Phase 2G: concept-conditioning experiment

Protocol established September 12, 2026, before training or model evaluation.
This is a research increment after the Phase 2A–2F engineering alpha.

## Hypothesis and scope

The Phase 2D encoder supplies the same program input for several teacher layouts.
Squared-error supervision can therefore average different arrangements. Phase 2G
tests whether supplying an independently selected concept token improves proposal
prediction, then measures whether that improvement survives strict repair.

The five tokens select the existing deterministic teacher controls. The token is
chosen before generation and is recovered by the generator's stable concept ID,
never by inspecting geometry, score or model output. This work does not introduce
new topology families, external data, a learned ranker or a new serving engine.

## Prospective data

`ml/configs/phase2g-v1.json` fixes all cohort seeds, counts, training seeds,
architecture, optimizer, epochs, repair budget and decision thresholds.

- 120 training briefs, 32 validation briefs and 100 reserved test briefs.
- Exclude all Phase 2A benchmark, Phase 2C pilot, Phase 2E stress and Phase 2F
  development/validation/test/stress model-input keys.
- A key combines room counts and unordered footprint dimensions. Changes to
  budget, style or orientation cannot move the same geometry input into a new split.
- Keep each brief's concept controls in one cohort; reject later cross-cohort
  near-duplicate geometry before training and record exclusions.
- Use the existing source-admission, canonical geometry, duplicate grouping,
  immutable dataset and integrity checks. Exact duplicate targets are removed by
  the established pipeline; controls with identical geometry may lose a duplicate
  row. Both trained arms use exactly the same retained rows.
- Store concept IDs in a separate checksummed mapping. The model receives only
  program features, requested relationships and the selected token.
- Holdout targets are prepared solely for deterministic admission/deduplication.
  This increment trains on training rows and evaluates validation only. There is
  deliberately no command to score the reserved holdout.

Initial data construction admits 1,243 plans: 592 training, 158 validation and
493 reserved test targets. Seventeen exact duplicate targets were removed.
These are generated synthetic targets, not independent architectural examples.

## Paired experiment

Run all three declared seeds: 20260912, 20260913 and 20260914. Report every seed;
do not choose the best one after seeing validation outcomes.

For each seed, train two models for the same 120 epochs, with identical hidden
size 64, four message-passing layers, batch size 32 and Adam learning rate 0.002:

1. **Conditioned:** add a learned concept embedding to each room representation.
2. **Token-ablated:** identical architecture, parameter count, initial weights,
   targets and minibatch order; replace every concept token with zero.

Embeddings start at zero, so both arms begin with identical predictions.
Select each checkpoint by validation loss using the same rule. Neither arm uses
test loss for selection. Checkpoints include tensor, data, context and source-code
identities, complete training histories and validation predictions.

A train-only mean for each concept/room type supplies an additional cheap control.
The original Phase 2D model remains frozen; its old benchmark scores must not be
subtracted from scores on these new cohorts.

## Matched downstream comparison

Evaluate four arms on the same 32 validation briefs: conditioned, token-ablated,
concept/type reference and an adjacency-only slot solver.

Every arm uses five proposals and exactly ten attempted repairs: two passes over
the same five templates. Each solve receives a deterministic work cap of 0.03,
one worker and fixed seeds: total cap 0.30 per brief. This is an OR-Tools work
budget, not a wall-clock duration. Hard constraints, adjacency weights, strict
validation, 0.025 concept separation, bounded reflow and 20,000-node selection
budget are shared.

Each selected concept token supplies the proposal for the corresponding template.
The solver-only control receives no model predictions or fitted reference. It
removes proposal displacement from the objective and tie-breaking; all other
constraints, templates, attempt counts and validation remain the same. This is a
strong within-family control, not an unrestricted architectural solver.

Record all failed attempts and briefs. A shortfall or rejected set fails the
five-concept contract and remains in the benchmark denominator. Never pad results
with duplicate concepts. Report raw validity separately from post-repair validity,
plus adjacency, diversity, budget fit, displacement and observed warm CPU p95.
Cold startup, HTTP transport and concurrent request queueing are outside timing.

## Decision rules

The engineering CI gate requires both training runs to learn relative to their
initial validation loss, complete case accounting, equal attempt budgets and
five strictly valid, distinct concepts from all four arms on every validation
brief. A failed research hypothesis must remain visible even if engineering passes.

Exploratory neural benefit requires all of:

- at least 10% lower validation coordinate MAE versus the paired token-ablated arm;
- positive lower endpoints of paired 95% adjacency-difference intervals against
  each control (2,000 bootstrap samples; brief is the resampling unit);
- no budget-fit or benchmark-diversity regression against the controls;
- five strictly valid distinct plans per brief and observed warm CPU p95 below 5s.

Intervals are exploratory and conditional on a training seed. Report the three
seed outcomes separately; do not treat seeds or the five concepts as additional
independent briefs. Aggregate summaries must bind the same protocol/data and list
all seeds, including unsuccessful ones.

Passing this development experiment does not qualify the model for promotion.
Any selected method still needs a prospectively frozen holdout evaluation,
independently licensed real-plan validation and blinded human preference above
60%. The deterministic application default and frozen experimental engine remain
the existing Phase 2F paths.

## Reproduction

Install the existing free application/test, solver and CPU ML requirements:

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-ml.txt
python -m archai_ml.benefit prepare --output conditioning-artifacts/data
python -m archai_ml.benefit train-pair --data conditioning-artifacts/data \
  --output conditioning-artifacts/seed-20260912 --seed 20260912
python -m archai_ml.benefit compare --data conditioning-artifacts/data \
  --runs conditioning-artifacts/seed-20260912 \
  --output conditioning-artifacts/comparison-20260912 --enforce
```

Repeat the train/compare commands for the other two declared seeds. Output
directories must be new. Generated data, checkpoints and full case diagnostics
stay outside tracked source. Commit compact reports after evaluating all seeds.
