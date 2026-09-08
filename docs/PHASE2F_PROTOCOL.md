# Phase 2F prospective protocol

Frozen before new cohort evaluation on September 8, 2026.

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
