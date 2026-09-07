# Phase 2D: learned coordinate accuracy improves; geometry release gate fails

The first supervised graph model reduces held-out coordinate MAE by **49.98%**
against a train-fitted mean-per-type reference. Every raw test proposal still has
overlapping rooms. Phase 2D establishes a reproducible learned research baseline;
it does not qualify the neural model for product use.

Experiment executed **September 5, 2026**; reviewed September 7, 2026.
[Exact experiment and artifacts](https://github.com/Shaurya-S0603/ArchAI/actions/runs/33982821297).
The ML job passed; the initial backend job found import-order lint issues,
which were corrected separately without changing the model or training configuration.
See [machine-readable evidence](phase2d-baseline.json).

## Frozen experiment

| Item | Value |
|---|---|
| Model | `room-graph-regressor-v1`, 60,261 parameters |
| Architecture | Four message-passing layers, width 64, box and symmetric edge heads |
| Data | Admitted synthetic pilot; 477 train / 55 validation / 60 test plans |
| Groups | 97 train / 11 validation / 12 test building/duplicate groups |
| Training | 120 epochs, batch 32, Adam 0.002, seed 20260906 |
| Selection | Lowest validation loss, epoch 96; test unused for selection |
| Runtime | CPU, one thread, Python 3.12.14, PyTorch 2.10.0+cpu |
| Validation loss | 0.145535 at initialization to 0.041907 at selected checkpoint |
| Source commit | `d98423c405fc278cd2b56b6b59dbc5ccd3419f89` |

Dataset digest: `e0efc4064fec21e0ca430ae356705052ba6002c70908fc3470606ddc944fd9aa`.
Tensor-state digest: `344a53149ef17be0a3b21e5284c4df742c27c59852629cbfbbc788d7a543f3c1`.
Full source/environment evidence is in the JSON report and checkpoint metadata.

## Held-out results

All metrics below use 60 plans containing 735 rooms. Coordinate errors use
normalized top-left x/y and width/depth. The reference is fitted only on training
targets; it is not the existing heuristic or CP-SAT generator.

| Metric | Train-only type reference | Learned model |
|---|---:|---:|
| Coordinate MAE, lower is better | 0.211610 | **0.105837** |
| Coordinate MSE, lower is better | 0.059379 | **0.027606** |
| Mean room IoU | 0.062762 | **0.096222** |
| Observed-adjacency F1 | 72.37% | **76.35%** |
| All rooms within footprint | 100% | 100% |
| All minimum room areas met | 100% | 100% |
| Plans without overlaps | 0% | 0% |
| Combined raw geometric validity | 0% | 0% |

IoU remains low, and lower coordinate error does not make a plan usable. Training
against several teacher layouts for the same room program encourages regression
toward incompatible average positions. This is a plausible mechanism for the
observed overlaps, not a demonstrated causal attribution. The synthetic teacher
also limits variation and cannot establish real-plan generalization.

Validation minimum-area pass rate is 90.91%, despite 100% on this small test set.
No minimum-area guarantee is claimed. Adjacency F1 measures predicted shared-wall
labels, not actual constructed doors or connected circulation. These metrics
are not interchangeable with the Phase 2A/2B generator comparison metrics.

## Verification and release decision

The optional ML suite has 28 passing tests and 98.11% statement coverage.
Tests cover target exclusion from inputs, graph conditioning, padding/gradient
masks, strict split selection, train-only reference fitting, deterministic repeat
training, immutable output, checkpoint integrity and dataset binding, metrics,
CLI paths, and fitting a small training batch.

The learning smoke gate passes: validation loss improves 71.21% from initialization.
The neural product-release gate remains blocked by overlap and unverified topology,
minimum dimensions, diversity, latency, stress behavior and human preference.
The existing production generator continues to provide validated concepts.

## Prioritized Phase 2E work

1. Add deterministic projection/repair with mandatory program, minimum area and
   dimensions, no-overlap, boundary and circulation gates; reject infeasible proposals.
2. Compare the complete repaired candidate with the frozen heuristic and solver.
   Record repair displacement, failure rates and whether learned proposals help.
3. Add a representation that can express multiple layouts, then test at least
   four distinct valid concepts from five results; measure CPU p95 and 1,000 briefs.
4. Expand diverse admitted teachers and establish an independent licensed holdout
   before claiming real-world improvement; keep Kaggle sources quarantined.

No user decision is needed for the repair sprint. External-data admission still
requires the intended-use rights and source review in the existing dataset policy.

Full dataset, weights, history, predictions and contact sheet are in the
`phase2d-learned-baseline` artifact on the linked run; that initial artifact expires
October 5, 2026. New CI runs produce fresh artifacts. Source and the frozen config
remain in Git for reproduction; use [the training guide](../docs/LEARNED_BASELINE.md).
