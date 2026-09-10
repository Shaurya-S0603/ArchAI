# ArchAI project status

**Updated:** September 10, 2026

**Development preview:** `v0.2.0-alpha.1` — Phase 2A–2F engineering delivery

**Release review:** [PR #2](https://github.com/Shaurya-S0603/ArchAI/pull/2)

Phase 2F closes the synthetic five-concept generation and experimental serving
gates. The full model remains unqualified for default promotion: independent
real-plan validation, human preference and neural quality benefit remain open.
The default application uses the deterministic generator.

## Delivered against the execution plan

| Increment | Delivered |
|---|---|
| 2A–2B | Frozen evaluation, transparent metrics and optional CP-SAT baseline |
| 2C | Governed room graphs, grouped splits and 592 admitted synthetic plans |
| 2D | Reproducible 60,261-parameter CPU model; frozen epoch-96 checkpoint |
| 2E | Strict proposal repair, topology validation and matched comparison |
| 2F | Bounded distinct search, verified experimental serving/fallback and fresh qualification |

## Evidence and release gates

| Gate | Evidence | Status |
|---|---|---|
| Fresh development/validation | 32 + 32 briefs, five valid distinct plans each | Pass |
| Locked release holdout | 100 briefs, 500 strict valid distinct plans | Pass |
| Adjacency gain | 65.36% baseline to 99.14%, +33.78 percentage points | Pass |
| Warm CPU p95 below 5 seconds | 0.799 s holdout; 0.785 s stress | Pass on measured runner |
| 1,000-brief stress | 5,000 valid distinct plans; zero failed briefs/crashes | Pass |
| Experimental API and fallback | Repeated-model responses, rejection paths and missing-model fallback tested | Pass |
| Neural superiority | Matched reference adjacency 99.67%; both return five distinct plans | Open |
| Independent licensed real plans | No external source admitted | Open |
| Blinded preference above 60% | No human preference study completed | Open |
| Learned ranking | Transparent metric ranker retained; preference data required | Open |

All raw neural proposals still overlap; strict repair is mandatory. Diversity
covers room proportions within the supported corridor family. Timing excludes
cold startup, concurrent queueing and HTTP transport.

The [qualification report](../reports/phase2f-qualification.md) includes exact
model/data/cohort identities, all observed metrics, run/artifact links and the
initial budget-gate failure. The correction charges the complete building
footprint consistently; no geometry, diversity or comparison threshold was relaxed.
Saved projects with an old cost version are reanalyzed when loaded.

## Verification and repository hygiene

The qualification commit passes all eight CI jobs: backend, baseline, solver,
dataset, learned model, repair, diversity and Chromium/accessibility. The ML/serving
suite has 71 passing tests at 98.22% coverage. The final local backend suite has
87 passing tests at 94.07%, including saved-cost refresh. Two-worker/four-thread
Gunicorn generation and PDF export pass. Python lint, JavaScript syntax and
documentation links are clean.

Version/configuration/documentation changes and saved-cost refresh follow the
qualification commit; the model, generation algorithm and cohorts are unchanged.
Standard CI repeats development/validation gates. The published holdout/stress
regression can be requested manually; future model tuning needs a new holdout.

Historical release notes are consolidated in [the changelog](../CHANGELOG.md).
Frozen reports, source provenance and the small QA fixture are retained.
Datasets, checkpoints, databases, build output and runtime reports remain outside
tracked source. Temporary feature-only CI triggers are removed from the alpha.

## Prioritized next sprint

1. Demonstrate neural benefit using identical repair budgets and new evaluation
   cohorts; expand beyond the deterministic corridor teacher family.
2. Review and admit a licensed real-plan source, then validate its adapter and
   held-out generalization.
3. Establish blinded, consented pairwise preference evaluation; learn ranking only
   when suitable evidence exists.
4. Revisit default neural promotion after those gates pass.

Decisions needed for later research: intended checkpoint distribution rights,
which real-plan source to admit after review, and the human evaluation protocol.
See [roadmap](ROADMAP.md) and [experimental setup](PHASE2F_PROTOCOL.md).
