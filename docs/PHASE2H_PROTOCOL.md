# Phase 2H: worst-collision training experiment

Declared October 6, 2026, before training this increment. Development experiment
only; the failed Phase 2G superiority gate is retained without reinterpretation.

## Hypothesis

The current objective already includes mean pairwise overlap. Averaging over all
room pairs can dilute a severe collision in a large plan. Add a penalty for each
plan's largest intersection, measured as a fraction of its footprint. This is a
single fixed intervention, not a weight search: base loss plus 0.5 times the mean
of the per-plan maximum pair intersections. Padding and self pairs are excluded.
The existing minimum-area and coordinate terms remain; smaller rooms must not be
mistaken for a quality improvement.

## Fixed comparison

Use the existing integrity-checked Phase 2G data: 592 training and 158 validation
targets, with all concepts of each brief in the same split. The validation set
has already been examined and remains development data. Its 493 reserved test
targets are not scored or used for selection; the experiment API rejects test
selection. No new real-plan data enters this study.

Run all three seeds in `ml/configs/phase2h-v1.json`. Both arms use the same concept
model, initialization, minibatch order, 120 epochs, optimizer, CPU threads and
parameter count. The base arm retains the original objective. The geometry arm
adds only the stated penalty. Both select checkpoints using the unchanged base
validation loss, allowing the base arm to reproduce the prior conditioned model.
Report every seed, initialization and checkpoint digests, failed gates and cases.
Do not pick the best seed or change the coefficient after inspecting results.

Compare base, geometry, train-only concept/type means and solver-only on the same
32 validation briefs. Preserve ten repair attempts, total deterministic work cap
0.30, strict validation, minimum separation 0.025, selection cap and cost semantics
from Phase 2G. A shortfall stays in the denominator and fails engineering checks.
Timing is measured separately with all training finished to avoid CPU contention;
record warm single-request p95 and the actual environment.

## Prospective decision rules

Engineering requires matching initial states and training budgets, learning in
both arms, complete accounting, identical repair budgets and five strict distinct
layouts per brief from every arm. These checks are independent of research success.

The development signal requires all of the following in each reported seed:

- at least 20% lower mean per-plan worst overlap than the paired base model;
- no more than 5% relative regression in raw coordinate MAE;
- lower endpoint of the paired 95% adjacency-difference interval at least -0.005
  against each control (a predeclared 0.5 percentage-point noninferiority margin);
- no diversity or budget-fit regression against any control;
- five strict distinct plans per brief and observed warm CPU p95 below five seconds.

Raw overlap summaries are descriptive, not independent-room significance tests.
Adjacency intervals use 2,000 bootstrap samples with brief as the resampling unit,
reported separately by seed. The reference's 100% validation adjacency makes the
old positive-superiority requirement unreachable on this cohort. Noninferiority
here is a new development screen, not a retroactive Phase 2G pass or proof of
neural benefit. Do not pool 3 seeds into 96 independent briefs.

Even a successful development screen requires a newly frozen qualification plan,
holdout confirmation, broader topology and independently licensed real-plan
evaluation, plus the existing blinded human-preference requirement. This module
does not change the default generator or the Phase 2F serving checkpoint.

## Reproduction

Install the existing development and CPU ML requirements, then:

```bash
python -m archai_ml.benefit prepare --output geometry-artifacts/data
python -m archai_ml.geometry train-pair --data geometry-artifacts/data \
  --output geometry-artifacts/seed-20260912 --seed 20260912
python -m archai_ml.geometry compare --data geometry-artifacts/data \
  --runs geometry-artifacts/seed-20260912 \
  --output geometry-artifacts/comparison-20260912 --enforce
```

Repeat for 20260913 and 20260914. Finish training before timing comparisons.
Output paths must be new. Checkpoints, full cases and data remain outside Git;
compact results and all identities are committed after the declared experiment.
