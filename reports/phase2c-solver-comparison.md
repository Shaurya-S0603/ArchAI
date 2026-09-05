# ArchAI Phase 2B Candidate Comparison

- Application: `0.2.0-dev.3`
- Baseline: `deterministic-baseline`
- Candidate: `cp-sat-v1`
- Dataset SHA-256: `7a545e2b28422980a8c60ffe888504300d2583a2de3aa36bdc29b7db9d7f9533`
- Promotion gate: **PASS**

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Generation success | 100.0% | 100.0% | +0.0% |
| Five-concept contract | 100.0% | 100.0% | +0.0% |
| Hard-constraint pass | 100.0% | 100.0% | +0.0% |
| Room-program match | 100.0% | 100.0% | +0.0% |
| Adjacency satisfaction | 65.5% | 99.4% | +33.9% |
| Concept diversity | 0.2386 | 0.1642 | -0.0744 |
| Budget fit | 60.8% | 60.6% | -0.2% |
| Accessibility alignment | 100.0% | 100.0% | +0.0% |
| User alignment | 96.1% | 96.1% | -0.0% |

## Promotion gates

| Gate | Required | Actual | Status |
|---|---:|---:|---|
| candidate_regression_gates | True | True | PASS |
| adjacency_gain | 0.05 | 0.3385 | PASS |
| candidate_diversity | 0.08 | 0.1642 | PASS |
| budget_regression | -0.01 | -0.002 | PASS |
| alignment_regression | -0.01 | -0.0002 | PASS |

> Passing this comparison permits continued research and optional integration;
> it is not architectural, regulatory, accessibility, or structural certification.
