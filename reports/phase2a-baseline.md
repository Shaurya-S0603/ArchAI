# ArchAI Generator Benchmark

- Application: `0.2.0-dev.1`
- Candidate: `deterministic-baseline`
- Dataset SHA-256: `7a545e2b28422980a8c60ffe888504300d2583a2de3aa36bdc29b7db9d7f9533`
- Evaluated: `2026-09-03T03:54:43+00:00`
- Overall gate: **PASS**

## Summary

| Metric | Result |
|---|---:|
| Cases evaluated | 100 |
| Generation success | 100.0% |
| Five-concept contract | 100.0% |
| Hard-constraint pass | 100.0% |
| Room-program match | 100.0% |
| Adjacency satisfaction | 65.5% |
| Mean diversity score | 0.2386 |
| Budget fit | 60.8% |
| Accessibility alignment | 100.0% |
| User alignment | 96.1% |

## Regression gates

| Metric | Minimum | Actual | Status |
|---|---:|---:|---|
| case_success_rate | 1.0 | 1.0 | PASS |
| concept_count_pass_rate | 1.0 | 1.0 | PASS |
| hard_constraint_pass_rate | 1.0 | 1.0 | PASS |
| program_match_rate | 1.0 | 1.0 | PASS |
| mean_adjacency_satisfaction | 0.6 | 0.6554 | PASS |
| mean_diversity_score | 0.08 | 0.2386 | PASS |

> These metrics compare generator candidates; they are not building-code,
> structural, accessibility, or professional design certification.
