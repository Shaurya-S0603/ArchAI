# Phase 2G: concept conditioning results

Evaluated September 14, 2026; recorded September 15, 2026 for
`v0.2.0-alpha.2`. **Engineering gates pass; neural benefit after repair does not.**

An explicit concept token reduces validation coordinate error by 35.89–36.55%
against an otherwise identical model with its token held constant. Repaired
diversity improves by 31.42–35.14% against that ablation. However, all raw outputs
still overlap, and repaired adjacency and diversity remain below the simpler
concept/type reference and solver-only controls. The experiment supports using
concept conditioning for better synthetic target prediction; it does not justify
promoting this model into the application.

## Experiment and data

The [prospective protocol](../docs/PHASE2G_PROTOCOL.md) fixes three training seeds,
all data identities and matched repair budgets before model evaluation. Both
trained arms have 60,581 parameters, identical initial predictions and batch
order, and 120 training epochs. Each checkpoint is selected by validation loss.
The concept/type reference is fitted on training data only. The solver-only
control uses no learned or fitted proposal.

| Cohort | Independent briefs | Retained synthetic targets | Model use |
|---|---:|---:|---|
| Training | 120 | 592 | Parameter fitting |
| Validation | 32 | 158 | Checkpoint selection and this comparison |
| Reserved test | 100 | 493 | Not scored |

All previously evaluated program keys are excluded. Seventeen exact duplicate
targets are removed before fitting. The reserved test targets are prepared only
for deterministic admission and duplicate checks. The three runs reuse the same
32 validation briefs; they are not 96 independent evaluation briefs. Validation
results are exploratory because these targets also select checkpoints.

## Raw prediction

MAE is normalized room-coordinate error; lower is better. Raw adjacency F1
measures supervised shared-boundary labels and differs from the desired-adjacency
satisfaction measured after repair.

| Training seed | Selected epoch, conditioned / ablated | Conditioned MAE | Ablated MAE | MAE reduction | Conditioned / ablated adjacency F1 |
|---|---|---:|---:|---:|---:|
| 20260912 | 92 / 115 | 0.064654 | 0.101896 | 36.55% | 82.67% / 75.24% |
| 20260913 | 75 / 105 | 0.064782 | 0.101610 | 36.24% | 82.53% / 76.41% |
| 20260914 | 70 / 86 | 0.064851 | 0.101154 | 35.89% | 82.04% / 75.70% |

The train-only concept/type reference has MAE 0.189310 and adjacency F1 72.95%.
All 158 raw validation plans overlap in both trained arms for every seed. The
conditioned model meets the measured minimum-area check on all validation plans,
but its combined raw geometry pass rate is 0%. Strict repair remains mandatory.

## Identical-budget repair comparison

Every arm attempts ten solves per brief, each with a deterministic work cap of
0.03: 320 attempts for 32 briefs per arm and seed. All attempts succeed, and all
four arms return five strictly valid, distinct layouts for every brief. Reflow,
selection, validation and separation thresholds are shared.

| Seed | Arm | Desired adjacency | Diversity | Mean displacement | Warm CPU p95 |
|---|---|---:|---:|---:|---:|
| 20260912 | Conditioned | 98.99% | 0.2271 | 0.098156 | 1.075 s |
| 20260912 | Token-ablated | 99.27% | 0.1728 | 0.103592 | 1.083 s |
| 20260913 | Conditioned | 99.13% | 0.2303 | 0.098897 | 1.062 s |
| 20260913 | Token-ablated | 99.48% | 0.1750 | 0.104434 | 1.060 s |
| 20260914 | Conditioned | 98.98% | 0.2269 | 0.100188 | 0.818 s |
| 20260914 | Token-ablated | 99.28% | 0.1679 | 0.104652 | 0.797 s |
| All seeds | Concept/type reference | 100.00% | 0.2319 | 0.191078 | 0.831–1.105 s |
| All seeds | Solver-only | 99.89% | 0.2428 | Not applicable | 0.660–0.887 s |

The last two rows share quality results across seeds because neither control
trains a model; each run's exact timing remains in the JSON report. Budget fit is
68.75% for every arm under `gross-footprint-v2`. Rearranging rooms cannot change
the charged building footprint. Accessibility and program-match gates pass for
all arms. Timing is warm single-request CPU inference and repair on the measured
GitHub runner; it excludes checkpoint load, HTTP and concurrent queueing.

Conditioning reduces mean repair displacement by 4.26–5.30% against the ablation.
This improvement does not translate into higher desired-adjacency satisfaction.
The reference and solver-only controls both exceed the conditioned model's
diversity. No overall neural quality claim passes the declared rules.

## Paired adjacency differences

Values below are percentage-point differences, conditioned minus control.
Intervals use 2,000 paired bootstrap samples over briefs. They are exploratory
95% percentile intervals conditional on each training seed, not pooled evidence
over independent runs or a held-out architectural quality study.

| Seed | Against token ablation | Against concept/type reference | Against solver-only |
|---|---|---|---|
| 20260912 | −0.274 [−0.807, +0.057] | −1.006 [−1.872, −0.314] | −0.892 [−1.648, −0.256] |
| 20260913 | −0.350 [−0.989, +0.055] | −0.871 [−1.678, −0.220] | −0.757 [−1.437, −0.189] |
| 20260914 | −0.293 [−0.990, +0.221] | −1.016 [−2.049, −0.227] | −0.903 [−1.897, −0.147] |

## Gate decision

| Gate | All three seeds |
|---|---|
| Both models learn; complete accounting; equal attempt budgets | Pass |
| Five strictly valid, distinct concepts from every arm | Pass |
| At least 10% lower raw MAE than token ablation | Pass |
| Positive adjacency interval against every control | Fail |
| No budget or diversity regression against controls | Fail: diversity |
| Observed warm CPU p95 below five seconds | Pass |
| Overall validation neural benefit | Not demonstrated |
| Qualified model release | No |

No seed is selected as a winner. All results, including failed research gates,
are retained. Neither the deterministic application default nor the frozen
Phase 2F experimental serving model is replaced by this research checkpoint.

## Verification and identities

[All eleven CI jobs passed](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34825488348)
on the implementation published at
[`953b608`](https://github.com/Shaurya-S0603/ArchAI/commit/953b608197126e16470a7915322d7199397853e1).
CI checked PR merge commit `8946d76eb2106e4b657784a2b61e921e37bf5876`; both commits
have tree `7faadd60ceaf745b8c4657f73e8e3610ebfa637b`.

- Backend: 93 passed, four ML modules skipped without PyTorch, 93.83% coverage.
- Dedicated ML/serving/research suite: 84 passed, 97.57% coverage.
- Frozen Phase 2D training reproduces tensor digest
  `344a53149ef17be0a3b21e5284c4df742c27c59852629cbfbbc788d7a543f3c1`.
- Phase 2G records digest:
  `b93e367c78c62344567205ecc592207f1700c8eae6e797071a1cee7ae6c1a1fd`.
- Context digest:
  `8cd345030ad00141172e23a10cc1fdb59e94369fb194af93ef4f729e02738d0c`.
- Protocol digest:
  `fb91977549d87939f6ab298e66e783a5845c478357cbcb3c96d7df6aa5fe6d1d`.
- Environment: Python 3.12.14, PyTorch 2.10.0+cpu, OR-Tools 9.15.6755,
  one CPU thread and deterministic algorithms.

The [machine-readable report](phase2g-conditioning.json) preserves every seed's
metrics, selected epochs, model hashes, intervals, failures and provenance.
Full checkpoints and case diagnostics are available as expiring CI artifacts:
[20260912](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34825488348/artifacts/10339992599),
[20260913](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34825488348/artifacts/10340108841),
[20260914](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34825488348/artifacts/10340167112).
Source, configuration, data identities and compact evidence are committed for
reproduction after artifact expiry. Release metadata and these reports follow
the evaluated implementation; they do not tune the experiment.

## Prioritized follow-up

1. Inspect the validation briefs where learned displacement loses adjacency to
   the strong controls. Test geometry-aware training or discrete slot prediction
   with the same matched budgets, raw validity and downstream metrics. Freeze the
   next hypothesis before running it; keep the reserved holdout unscored.
2. Broaden synthetic topology coverage and review an independently licensed
   real-plan source. More examples from this teacher alone cannot establish
   generalization beyond corridor/perimeter layouts.
3. Set up blinded, consented preference evaluation before learned ranking.
4. Consider serving integration only after downstream benefit, a prospectively
   locked holdout, licensed real-plan evaluation and preference gates pass.

No user decision blocks further synthetic research. Real-plan admission requires
the intended checkpoint distribution rights and an acceptable source; human
evaluation requires an agreed participant and consent protocol.
