# ArchAI Generator Evaluation Protocol

## Objective

Every future heuristic, constraint-solver, neural, or hybrid generator must be
measured through the same candidate interface: a validated `DesignBrief` produces
five `Layout` objects. Hard geometry and topology checks remain deterministic and
outside learned components.

## Phase 2A benchmark

The committed `data/benchmarks/v1` fixture set contains 100 deterministic synthetic
briefs spanning supported room counts, optional rooms, styles, currencies,
accessibility settings, sustainability settings, budgets, site sizes, and site
orientations. `manifest.json` pins its provenance and SHA-256 digest.

## Metrics

| Metric | Definition | Gate |
|---|---|---:|
| Case success | Briefs returning without a generator error | 100% |
| Five-concept contract | Briefs returning exactly five concepts | 100% |
| Hard-constraint pass | Concepts with no deterministic compliance errors | 100% |
| Program match | Requested room multiset retained without additions or omissions | 100% |
| Adjacency satisfaction | Weighted requested relationships achieved, capped per brief | at least 60% |
| Diversity | Pairwise room-center displacement normalized by site diagonal | at least 0.08 |
| Budget fit | Concepts at or below the supplied concept-stage budget | reported only |
| Accessibility alignment | Target door widths and turning-zone coverage | reported only |
| User alignment | Weighted program, validity, style, accessibility, and budget score | reported only |

Budget and user-alignment values are reported but not release gates in Phase 2A
because the deterministic baseline uses the full available footprint instead of
optimizing floor area against cost. They are retained so Phase 2B has a visible
improvement target.

## Frozen baseline

The first 100-case deterministic-baseline report records:

| Metric | v0.2.0-dev.1 baseline |
|---|---:|
| Generation success | 100.0% |
| Five-concept contract | 100.0% |
| Hard-constraint pass | 100.0% |
| Program match | 100.0% |
| Adjacency satisfaction | 65.54% |
| Diversity | 0.2386 |
| Budget fit | 60.8% |
| Accessibility alignment | 100.0% |
| User alignment | 96.1% |

The exact machine-readable results are stored in
`reports/phase2a-baseline.json`; the concise report is
`reports/phase2a-baseline.md`.

## Running the benchmark

```bash
python -m archai.evaluation --enforce
```

Optional JSON and Markdown destinations can be supplied with `--json` and
`--markdown`. `--enforce` returns a non-zero status when any frozen threshold
fails, which makes the benchmark suitable for CI.

## Phase 2B solver comparison

The optional `cp-sat-v1` candidate is evaluated against the frozen deterministic
baseline on the same dataset digest. It must retain the baseline regression gates,
improve adjacency by at least 0.05, retain at least 0.08 diversity, and avoid a
budget-fit or user-alignment regression greater than 0.01.

```bash
python -m pip install -r requirements-solver.txt
python -m archai.evaluation.comparison --enforce \
  --json reports/phase2b-comparison.json \
  --markdown reports/phase2b-comparison.md
```

The v0.2.0-dev.2 frozen comparison records:

| Metric | Baseline | CP-SAT candidate | Delta |
|---|---:|---:|---:|
| Generation success | 100.0% | 100.0% | 0.0% |
| Hard-constraint pass | 100.0% | 100.0% | 0.0% |
| Program match | 100.0% | 100.0% | 0.0% |
| Adjacency satisfaction | 65.54% | 98.41% | +32.87% |
| Diversity | 0.2386 | 0.1745 | -0.0641 |
| Budget fit | 60.8% | 60.6% | -0.2% |
| Accessibility alignment | 100.0% | 100.0% | 0.0% |
| User alignment | 96.1% | 96.1% | -0.02% |

The promotion gate passes, but the solver remains an optional research candidate.
The production API continues to use the transparent deterministic fallback until
integration latency, failure handling, and real-plan evaluation are complete.

## Candidate promotion rule

A candidate may replace the deterministic production default only when it:

1. passes every hard regression gate;
2. exceeds the baseline on predeclared target metrics using validation data;
3. confirms the result on the frozen test split after selection;
4. documents runtime, hardware, seed variance, data license, and failure cases;
5. retains deterministic repair and the no-GPU fallback;
6. does not represent benchmark scores as regulatory or professional approval.

## Known limitations

The current benchmark evaluates supported synthetic briefs, not real household
behavior, architectural preference, jurisdictional rules, structural safety, or
construction readiness. Public fixtures can be overfit. Phase 2 must therefore
add license-reviewed real-world evaluation data before making broader quality
claims.
