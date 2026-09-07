# v0.2.0-dev.4 — Phase 2D supervised graph baseline

This development increment adds ArchAI's first trained neural research model.
It establishes reproducible training and held-out evidence; overlap failures
keep the production application on the deterministic generator.

## Changes

- Add an optional CPU PyTorch package with four graph message-passing layers,
  bounded normalized room boxes and a symmetric adjacency head.
- Build program-only inputs with strict target separation and padding masks.
- Train using the admitted synthetic pilot, with validation-only checkpoint selection.
- Save immutable state-dict checkpoints, data/source/environment metadata and history.
- Verify checkpoints by hashes, vocabulary, configuration, dataset binding and finite weights.
- Add explicit split evaluation, a train-fitted reference, raw predictions and contact sheets.
- Add 28 ML tests and a sixth CI job, with an independent 90% ML coverage floor.

## Evidence

The frozen 120-epoch run uses 477 training and 55 validation plans and selects
epoch 96. On 60 test plans, normalized coordinate MAE is 0.105837 versus 0.211610
for the training-only reference, and adjacency F1 is 76.35% versus 72.37%.
The ML tests pass with 98.11% coverage. Full evidence, experiment dates and
artifact links are in [the report](../reports/phase2d-baseline.md).

## Unmet gates

Every raw test proposal contains overlapping rooms. Constraint repair, connected
door/circulation topology, minimum dimensions, diverse valid candidates, CPU
p95, 1,000-brief stress behavior, human preference and real-plan generalization
remain unverified. External datasets remain quarantined. No new production
generator or reinforcement-learning system is included.

See [the reproduction guide](LEARNED_BASELINE.md) and [model card](MODEL_CARD.md).
