# ArchAI project status

**Updated:** September 7, 2026
**Development version:** `v0.2.0-dev.5` — Phase 2E constrained neural repair
**Review:** `development` into `main`, draft PR #2

The repair component is implemented and evaluated. The complete learned generator
is not ready for product integration: distinct five-concept output and measurable
neural benefit remain open. The Flask application uses the deterministic generator.

## Delivered

| Area | Current capability | Evidence |
|---|---|---|
| Editor | SQLite persistence, room editing, topology, zoning, 2D/3D and exports | [Changelog](../CHANGELOG.md) |
| Evaluation | Frozen 100-brief benchmark and optional CP-SAT generator | [Protocol](EVALUATION_PROTOCOL.md) |
| Data | Governed canonical room graphs; 592 admitted synthetic plans | [Pipeline](TRAINING_DATA_PIPELINE.md) |
| Learning | Frozen 60,261-parameter CPU model, validation-selected epoch 96 | [Experiment](../reports/phase2d-baseline.md) |
| Repair | Constrained slot assignment, independent strict validation and distinct selection | [Contract](CONSTRAINT_REPAIR.md) |

## Phase 2E evidence and release gates

All 100 benchmark briefs return valid repair: 443 layouts, all with exact room
programs, valid dimensions/areas, no overlaps, complete footprint coverage,
connected doors, entry and habitable-room windows. The raw model overlaps on
every benchmark brief. Repair does not certify structural or regulatory compliance.

| Gate | Result | Status |
|---|---|---|
| At least one strict repair per benchmark brief | 100/100 | Pass |
| Adjacency gain over the heuristic | 65.54% to 99.48%, +33.94 percentage points | Pass |
| Four distinct concepts per brief | 79/100 | Open |
| Five-concept output contract | 72/100 | Open |
| Observed warm CPU p95 under 5 seconds | 0.970 s in the final feature run | Pass on measured runner |
| Neural improvement over matched repair reference | Adjacency 99.48% vs 99.62%; five-concept rate 72% vs 68% | Mixed; superiority unproven |
| Fresh-brief repair stress | 1,000/1,000 valid; 4,447 layouts; zero crashes | Pass for repair |
| Full five-concept stress contract | Five concepts for 71.1% of stress briefs | Open |
| Independent licensed real-plan validation | No external source admitted | Open |
| Blinded preference above 60% and product fallback integration | Not evaluated/integrated | Open |

The [repair report](../reports/phase2e-repair.md) contains run links, exact timings,
stress results, immutable model/data identities and the remaining generator gates.
The [roadmap](ROADMAP.md) records the next development slice.

## Verification and repository hygiene

CI separately verifies backend tests/coverage, baseline regression, solver
comparison, pilot integrity, ML/repair tests and frozen training, repaired-model
comparison, and Chromium/accessibility. The repaired research module has 53 tests;
the web/backend suite has 68, with 98.62% and 94.06% coverage respectively.
All seven jobs pass on the corrected Phase 2E feature commit. Runtime verification is performed in GitHub Actions;
local checks cover compiled source, JavaScript syntax, links and whitespace.

Historical release notes are consolidated in one changelog. Repeated README and
status material and obsolete feature-branch workflow entries are removed. Frozen
reports, benchmark inputs, source provenance and small QA fixtures are retained
because they support reproducibility. Generated datasets, checkpoints, databases,
build output and runtime reports belong outside tracked source. The production
Docker context is limited to web runtime files.

## Next actions and decisions

1. Phase 2F: improve distinct proposals/templates under the same strict constraints.
2. Use fresh development/validation briefs for iteration and a new locked release
   holdout; do not tune against the already reported benchmark/test results.
3. Demonstrate a neural contribution against the matched reference and strong
   CP-SAT baseline before production integration.
4. Complete real-plan source admission and blinded human evaluation. No decision
   is needed to continue synthetic research. Source licensing requires review
   before external data or restricted checkpoints are introduced.

Promotion of draft PR #2 to `main` remains a separate user decision.
