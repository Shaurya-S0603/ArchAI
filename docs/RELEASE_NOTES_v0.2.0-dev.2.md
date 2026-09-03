# ArchAI v0.2.0-dev.2

**Milestone:** Phase 2B - evaluated CP-SAT generator candidate

## Added

- optional OR-Tools 9.15 CP-SAT dependency and deterministic solver generator;
- named candidate registry and candidate-aware benchmark interface;
- baseline-versus-candidate JSON/Markdown comparison with enforced promotion gates;
- dedicated free-CPU GitHub Actions solver-comparison job;
- external dataset candidate register covering Kaggle discovery, original-source
  provenance, license compatibility, and checkpoint-redistribution review.

## Evaluation result

Across the frozen 100-case benchmark, `cp-sat-v1` returns five valid concepts for
every case and improves functional adjacency satisfaction from 65.54% to 98.41%.
It records 0.1745 diversity, 60.6% budget fit, 100% accessibility alignment, and
96.1% user alignment. Every predeclared Phase 2B promotion gate passes.

The solver is a research candidate, not the production API default. It does not
constitute a trained AI system, architectural certification, regulatory approval,
or evidence of real-world generalization.

## Reproduce

```bash
python -m pip install -r requirements-dev.txt
pytest --cov=archai --cov-fail-under=90
ruff format --check .
ruff check .
python -m archai.evaluation.comparison --enforce \
  --json reports/phase2b-comparison.json \
  --markdown reports/phase2b-comparison.md
```
