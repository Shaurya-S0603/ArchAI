# Phase 2F prospective protocol

Frozen before new cohort evaluation on September 8, 2026.

Amendment on September 10, before opening test/stress: development evaluation
exposed a cost-definition defect, not a generation failure. Two baseline variants
of development brief 13 had rounding gaps of 0.01296/0.02592 square metres and
received false budget passes. All candidates have the same building footprint.
Cost model `gross-footprint-v2` now bills that complete footprint, including
circulation and unassigned space, for every generator and edited plan. Interior
gaps cannot earn a discount and overlaps cannot add a surcharge. Budget flags use
the same exact budget threshold; comparison tolerances are unchanged. Reports
record the cost-model version and reject cross-version budget comparisons.
Historical reports retain their original room-area cost model. The initial
development gate failure remains part of the release evidence. Generation,
training, geometry checks, cohort identities and separation thresholds are unchanged.

The engineering target is five independently valid, pairwise distinct concepts,
with the Phase 2E separation threshold (0.025 of the footprint diagonal), strict
geometry tolerances and frozen Phase 2D model unchanged. The model remains an
experimental option; the default Flask generator stays deterministic.

The bounded candidate search adds corridor-position variants only when Phase 2E
selection has fewer than five concepts. Each variant recomputes both perimeter
strips coherently on the millimetre grid, preserving room order, a continuous
1.8 m corridor and complete coverage. Minimum dimensions and areas constrain the
feasible interval. All results pass the independent repair validator. Selection
searches for five mutually separated candidates; reflected copies do not count.
This adds room-proportion diversity within the existing corridor family, not new
building topologies or evidence of human preference.

`ml/configs/phase2f-v1.json` fixes sampling, search budget and cohort seeds/counts.
Fresh cohorts exclude the original benchmark, all 120 pilot brief programs and
the already evaluated Phase 2E 1,000-brief stress cohort. The grouping key is room
type counts plus unordered footprint dimensions; budget, style and reflection
changes cannot put the same model geometry input into different cohorts. Cohorts
exclude one another in development, validation, test, stress order. They share
the existing synthetic brief distribution and are not real-plan validation.

Iterate on 32 development briefs and verify on 32 validation briefs. Freeze the
implementation before opening the 100-brief test cohort and 1,000-brief stress
cohort. A failed test gate remains a reported failure; any subsequent tuning
requires a new protocol and holdout. Standard CI repeats development/validation
regressions; release qualification runs the locked cohorts separately.

Compare neural and train-only type-mean proposals through identical repair and
diversity processing, plus the deterministic baseline on the same inputs. Require
100% five-concept/program/strict-validity rates, existing comparison gates,
adjacency at least 10 percentage points above baseline and measured warm CPU p95
below 5 seconds. Stress requires 1,000 briefs, zero failed briefs, all five outputs
strictly valid and distinct. Record cold checkpoint load separately. Hardware and
dependency versions bound timing/reproducibility claims.

API integration uses a trusted operator-configured checkpoint path, cached per
worker. Missing dependencies, invalid checkpoints, shortfalls or rejected output
fall back to the existing deterministic generator with explicit response metadata.
Request JSON cannot choose a checkpoint or enable the experimental engine.

Passing these engineering gates permits the user-authorized Phase 2 development
preview merge. Independent licensed real-plan validation, blinded preference
above 60%, and demonstrated neural quality benefit remain model-qualification
requirements; no external data or trained weights are admitted to Git by this work.

## Reproduction and experimental serving

First reproduce the frozen checkpoint using [the training guide](LEARNED_BASELINE.md).
Keep its manifest, weights, history, reference and training report together. The
server accepts only the frozen synthetic data and tensor-state identities used
in the qualification report; an arbitrary valid checkpoint is insufficient.

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-ml.txt
python -m archai_ml.qualification --run ml/runs/phase2d-v1 \
  --output diversity-artifacts/development --stage development --enforce
python -m archai_ml.qualification --run ml/runs/phase2d-v1 \
  --output diversity-artifacts/release --stage release --enforce
```

Output directories must be new. Each contains checksummed JSON reports and
case-level diagnostics. The release command opens the prospectively locked test
and stress cohorts; do not use it to tune the generator.

To opt into experimental serving in a local Python deployment:

```bash
ARCHAI_GENERATOR=experimental-neural ARCHAI_MODEL_RUN=/absolute/path/to/run python app.py
```

The default `ARCHAI_GENERATOR=deterministic-baseline` requires no model or solver
installation. The default Docker image includes only that web runtime; experimental
serving needs the source checkout, optional requirements and a trusted local run.
Set configuration before starting workers. Restart workers after replacing a run;
there is no upload endpoint or live model reload. Each worker loads once and
serializes neural requests; concurrent queueing and cold startup are outside the
single-request warm CPU latency measurement.

Budget estimates use the complete building footprint in `gross-footprint-v2`.
Moving or resizing rooms inside an unchanged footprint does not alter the charged
area. Saved projects are reanalyzed under this cost version when loaded; historical
room-area quotes can therefore change. Budget optimization through smaller
building footprints is outside this candidate's geometry contract.

`POST /api/v1/layouts/generate` adds a top-level `generator` object:

```json
{"requested":"experimental-neural","used":"deterministic-baseline","fallback":true,"reason":"engine_unavailable"}
```

Successful experimental responses use `experimental-neural`, with `fallback:false`
and `reason:null`. Invalid candidates use `candidate_rejected`; the response never
includes checkpoint paths or exception details. Baseline output retains its
existing preliminary compliance reporting and is not relabeled as strict neural
output. The optional engine is a development feature, not the recommended default.
