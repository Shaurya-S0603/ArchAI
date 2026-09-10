# Phase 2D supervised graph baseline

Phase 2D adds an optional CPU research model and a reproducible experiment over
the admitted Phase 2C synthetic pilot. The default web application uses the
deterministic generator. Raw neural output requires constraint repair; Phase 2F
adds [experimental serving and qualification](PHASE2F_PROTOCOL.md).

## Reproduce

Use Python 3.12 in a fresh environment, from the repository root:

```bash
python -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-ml.txt
python -m archai.datasets pilot --output data/processed/pilot-v1 --count 120
python -m archai_ml train --dataset data/processed/pilot-v1 \
  --output ml/runs/phase2d-v1 --config ml/configs/phase2d-v1.json --enforce
python -m archai_ml evaluate --dataset data/processed/pilot-v1 \
  --run ml/runs/phase2d-v1 --output ml/runs/phase2d-test-v1 --split test
python -m archai_ml predict --run ml/runs/phase2d-v1 \
  --program ml/configs/example-program.json
pytest tests/test_ml.py tests/test_repair.py tests/test_diversity.py \
  tests/test_generation_engine.py tests/test_qualification.py \
  --cov=archai_ml --cov-fail-under=90
```

On Windows activate `.venv-ml\Scripts\activate` instead. The ML requirements file
uses the official CPU wheel index and pins PyTorch 2.10.0. It is installed
separately so the ordinary application and solver installs stay lightweight.
The optional `ml` packaging extra also declares PyTorch; prefer the documented
CPU index installation when avoiding CUDA packages.
[Official CPU installation instructions](https://pytorch.org/get-started/previous-versions/).

## Input and target contract

`archai_ml` is optional; the default web configuration never imports PyTorch. The data
adapter validates the Phase 2C dataset once and caches its rows. Callers must
select a nonempty train, validation or test split explicitly. No IDs, source IDs,
building IDs, split labels, observed boxes or observed edges enter model inputs.

Input programs contain `footprint_m: [width, depth]`, a list `room_types` with
4-32 supported entries, and optional `desired_adjacency` as zero-based index
pairs. Dimensions are metres, x increases rightward and y downward. Input types
use the fixed Phase 2C vocabulary; zero is padding. Unsupported fields and
non-finite dimensions are rejected. This research program format is separate
from the Flask survey API.

Each room receives a 16-dimensional learned type embedding and seven scalar
features: minimum area / footprint area, nominal target area / sum of nominal
targets, repeated-type instance index, type count / 32, footprint width / 80,
footprint depth / 80, and total room count / 32. Nominal areas come from the
existing room library, never observed room areas. Repeated types use their order
in the input program. Supervision follows Phase 2C's type/geometry canonical
ordering; this is a target-slot convention, not observed-coordinate conditioning.

Default desired edges use the existing functional type preferences, normalized
by five, with a minimum weight of 0.6 for corridor connections. Explicit input
edges have weight one. The pilot trains only on default desired graphs; behavior
on arbitrary user-supplied graphs is unvalidated.

Four residual message-passing layers of width 64 combine each node, its weighted
neighbor mean, and a masked global mean, with SiLU and LayerNorm. Padding is
removed from messages, pooling and supervision. The symmetric pair head predicts
observed shared-boundary adjacency; diagonals and padded pairs are excluded.

The box head predicts normalized `[x, y, width, depth]`. Sigmoid sizes and
`position = sigmoid(raw_position) * (1 - size)` keep positive boxes in bounds.
This does not enforce overlap, minimum areas, dimension minima, doors or
circulation connectivity. Phase 2D is a deterministic single-proposal regressor.
Stochastic generation and diverse candidate selection remain later work.

## Training and selection

The committed configuration freezes seed 20260906, 120 epochs, batch size 32,
learning rate 0.002, 64 hidden units and four layers before held-out evaluation.
Adam updates use training rows only and gradient-norm clipping at one. Python
and PyTorch are seeded, CPU threads are fixed to one and deterministic algorithms
are enabled. Runs log the package versions, platform, Git revision, actual Python
source digest, data digest and tensor-state digest. Same-environment repeated
training is tested; cross-platform or cross-version equality is not promised.
[PyTorch reproducibility guidance](https://docs.pytorch.org/docs/2.10/notes/randomness.html).

The fixed loss is box MSE + 0.1 area MSE + 0.05 adjacency BCE + 0.1 mean pairwise
overlap area + minimum-area shortfall squared. Boxes/areas use normalized units;
unordered valid room pairs exclude self edges. The reported epoch loss weights
batch means by plan count. Validation uses a fixed batch size and ordering.

The best validation loss selects a checkpoint; initialization is a valid candidate
if training never improves. `--enforce` requires strict validation improvement
over initialization and fails on non-finite training/output. It is a learning
smoke gate, not a model-release or superiority gate. The reference uses only
training room-type mean boxes and Laplace-smoothed type-pair adjacency frequency.
Held-out comparison against that reference is reported independently.

The pilot contains 477 training, 55 validation and 60 test plans, grouped by
building and geometry duplicates. Training reads test rows only through integrity
and split validation; it never scores them or uses them in optimization/selection.
The separate `evaluate --split test` command requires a completed frozen run.
Do not tune hyperparameters against this test result. This small public synthetic
split will need a new independent holdout for future architecture selection.

## Artifacts and evaluation

Training writes a new immutable directory containing a state-dict checkpoint,
training metadata, validation history, train-fitted reference and a file-hash
manifest. Loading checks the version, vocabulary, dataset binding, file checksums,
configuration, finite weights and tensor digest, then uses CPU
`torch.load(weights_only=True)`. Checksums are corruption checks, not signatures;
load checkpoints only from a trusted run/source.
[PyTorch checkpoint loading](https://docs.pytorch.org/docs/2.10/generated/torch.load.html).

Evaluation writes a separate immutable directory with a JSON report, raw boxes
and a target/prediction contact sheet. The sheet uses the first six sorted split
IDs so examples are not selected by prediction quality. Metrics are room-level
normalized box MAE/MSE and mean IoU, micro adjacency F1 at probability 0.5, and
whole-plan boundary, overlap and minimum-area pass rates. Overlap tolerance is
one square millimetre per pair; normalized boundary tolerance is 1e-6. The
geometric-valid rate combines those three checks only. It is not the complete
Phase 2A hard-constraint metric, and predicted edges are not constructed doors.

CI keeps existing backend coverage at 90% and independently enforces 90% coverage
for the optional ML package. It regenerates the admitted pilot, trains the frozen
configuration, evaluates the selected weights and uploads complete artifacts for
30 days. Runs/checkpoints are ignored by Git; committed source, configuration and
compact reports preserve reproduction after artifact expiry.

## Release gates and next sprint

The current model learns the heuristic teacher's rectangular corridor/perimeter
bias. Five teacher variations per program create a multimodal target; squared
error can average incompatible arrangements and produce overlapping rooms.
Lower coordinate error does not establish better usable plans than the heuristic
or CP-SAT solver. There is no learned generator in the production candidate registry.

Phase 2E now projects the frozen proposals through deterministic slot repair,
rebuilds topology, rejects failed solves and selects distinct valid concepts.
All 100 benchmark briefs return valid repairs, but only 72% return five concepts;
the matched reference has slightly better adjacency. See [repair contract](CONSTRAINT_REPAIR.md)
and [the comparison](../reports/phase2e-repair.md).

Phase 2F should improve proposal/template diversity and test neural contribution
against the same repair applied to a train-only reference. Define new development
and validation briefs before tuning; reserve a fresh locked holdout for release.
Diverse solver teachers and an independent, licensed real-plan holdout are needed
to assess generalization. Blinded human preference and application integration
remain open. Kaggle sources require their recorded source review to be satisfied.
