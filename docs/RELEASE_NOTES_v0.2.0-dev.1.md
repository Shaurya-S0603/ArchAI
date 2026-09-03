# ArchAI v0.2.0-dev.1

**Milestone:** Phase 2A - evaluated generative-intelligence foundation

**Status:** Development preview

## Added

- a deterministic, versioned 100-case synthetic residential benchmark;
- fixed 60/20/20 development, validation, and test splits;
- manifest-level provenance, MIT license, exclusions, and SHA-256 integrity;
- generator-independent validity, program, adjacency, diversity, budget,
  accessibility, and user-alignment metrics;
- JSON and Markdown report generation through `python -m archai.evaluation`;
- enforceable regression thresholds and a dedicated GitHub Actions benchmark job;
- dataset-governance and candidate-promotion protocols.

## Baseline result

The Phase 1 deterministic generator passes all Phase 2A release gates across 100
briefs. Adjacency satisfaction is 65.54%, diversity is 0.2386, and budget fit is
60.8%. These become explicit Phase 2B improvement targets rather than hidden
assumptions.

## Compatibility

- The browser workflow and `/api/v1` routes remain compatible with v0.1.
- Project schema version remains 3.
- No paid service, GPU, external dataset, or new runtime dependency is required.

## Boundary

This release does not contain a trained model. Benchmark results compare generator
candidates and do not certify architectural quality, accessibility, structural
safety, building-code compliance, or construction readiness.
