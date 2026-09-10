# Phase 2F qualification — September 10, 2026

The Phase 2A–2F engineering preview meets its declared synthetic generation gates.
It is packaged as `v0.2.0-alpha.1` with an operator-enabled experimental engine and
a deterministic default/fallback. It remains an unqualified model release pending
independent real-plan and human evaluation and demonstrated neural quality benefit.

[Qualification workflow](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34451335720)
passed all eight jobs on commit
[`864ddad`](https://github.com/Shaurya-S0603/ArchAI/commit/864ddadd1a6796f1ca3e1390b2b05dfcfc21a069).
[Case-level artifacts](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34451335720/artifacts/10142195701)
and [the complete JSON report](phase2f-qualification.json) preserve the evidence.

## Fresh cohort results

| Cohort | Briefs | Returned plans | Five distinct / strict valid | Warm CPU p95 |
|---|---:|---:|---:|---:|
| Development | 32 | 160 | 100% / 100% | 0.794 s |
| Validation | 32 | 160 | 100% / 100% | 0.776 s |
| Release holdout | 100 | 500 | 100% / 100% | 0.799 s |
| Stress | 1000 | 5000 | 100% / 100% | 0.785 s |

The 1,000-brief stress run had zero failed briefs and zero crashes. Eight individual
solver attempts were rejected safely; every brief still returned five validated
concepts. Maximum stress latency was 0.993 seconds.
Release checkpoint load was 0.737 seconds, reported separately.

## Locked 100-brief comparison

| Metric | Deterministic baseline | Neural + repair/diversity | Matched type-mean reference |
|---|---:|---:|---:|
| Adjacency satisfaction | 65.36% | 99.14% | 99.67% |
| Benchmark diversity score | 0.2411 | 0.1666 | 0.1530 |
| Budget fit, gross-footprint-v2 | 63.00% | 63.00% | 63.00% |
| Five returned concepts | 100% | 100% | 100% |

The neural pipeline gains 33.78 percentage points of adjacency over the baseline.
Its adjacency is 0.53 points below the matched reference. Both repaired pipelines
return five distinct concepts on every holdout brief. Mean normalized coordinate
repair displacement is 0.109565 for neural proposals and 0.195180 for the reference.
This supports lower proposal displacement, not overall neural superiority.
All raw proposals still overlap and are never served directly.

Diversity requires distinct geometry fingerprints and optimal repeated-type
matching with center separation of at least 0.025 of the footprint diagonal.
Whole-plan reflections do not count. Reflow adds room-proportion variation inside
the supported corridor family; it does not demonstrate varied building topology
or human preference.

## Reproducibility and cost correction

The model/data identities remain the frozen Phase 2D identities. Training again
selected epoch 96 with exactly the same tensor digest, PyTorch 2.10.0+cpu, Python
3.12.14, one CPU thread and deterministic settings. The prospective cohorts exclude
previous benchmark/pilot/stress programs and one another by room types plus
unordered footprint dimensions. Test and stress opened only after development
and validation passed on the fixed qualification commit. See the
[prospective protocol and reproduction commands](../docs/PHASE2F_PROTOCOL.md).

The first development run on September 8 failed the budget regression gate:
two baseline variants received false budget passes because rounded interior
partitions left tiny gaps. `gross-footprint-v2` now charges the complete building
footprint for every generator. Comparison thresholds, model weights, geometry
checks and cohort identities were not relaxed. Both sides were reevaluated before
test/stress opened. Historical room-area reports remain unchanged and are not
comparable on budget metrics. The initial failed result is retained in the JSON.

## Application and release evidence

- Experimental API smoke gates pass: correct engine, five results, successful status
  and identical repeated responses.
- The ML/serving suite passes 71 tests at 98.22% coverage.
- The final local backend suite passes 87 tests at 94.07% coverage, including
  legacy-cost refresh when saved projects load.
- Backend, frozen baseline, solver, dataset, learned model, repair, diversity and
  Chromium/accessibility CI jobs pass on the qualification commit.
- Two-worker/four-thread Gunicorn startup, generation and PDF export pass locally.
- Final packaging changes add version metadata, documentation, optional manual
  stress execution and legacy-cost refresh; the qualified generator is unchanged.

Warm latency describes sequential inference on the measured CI runner. Worker
queueing, cold startup, HTTP transport and other machines are not covered by that
number. No paid service, external dataset or tracked checkpoint is introduced.

## Remaining qualification and next sprint

1. Demonstrate neural quality benefit under identical repair budgets and a strong
   solver reference, using fresh development data and a new locked holdout.
2. Admit a licensed real-plan source and validate its adapter and generalization.
3. Collect blinded, consented preferences and meet the above-60% preference gate;
   train a learned ranker when suitable judgments exist.
4. Consider making neural generation the default only after those gates pass.

The current release uses transparent metric ranking. External source rights and
checkpoint distribution terms require review before admission; human evaluation
needs a reviewed protocol. The synthetic alpha retains its deterministic default
while those research gates remain open.
