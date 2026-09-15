# ArchAI Delivery Roadmap

## Phase 0 - Executable web foundation (complete)

- [x] Flask application and versioned JSON API
- [x] Responsive HTML/CSS/JavaScript design studio
- [x] Validated survey input
- [x] Five deterministic layout concepts
- [x] Generic rule checks and cost baseline
- [x] 2D drag editing, keyboard movement, and undo/redo
- [x] Interactive dependency-free 3D massing
- [x] JSON, SVG, and OBJ export
- [x] Windows, macOS/Linux, Docker, and Render launch paths
- [x] Automated backend tests

## Phase 1 - Architectural editor

- [x] room resizing with handles and minimum-dimension constraints;
- [x] explicit corridors, doors, windows, wall segments, and openings;
- [x] topology repair after edits;
- [x] furniture zones and accessibility clearances;
- [x] project persistence in SQLite with schema migrations;
- [x] printable plan sheets and PNG/PDF export;
- [x] end-to-end browser tests and WCAG 2.2 AA audit.

The `v0.1.0-dev.1` release completed Phase 1 with deterministic
zoning, printable PNG/PDF output, no-drag room editing, browser workflow tests,
and automated WCAG 2.2 A/AA checks.

Exit condition: a saved project can be edited, reloaded, printed, and exported
without geometry corruption. **Satisfied by the v0.1 development preview.**

## Phase 2 - Model development preview and qualification

The Phase 2A–2F engineering sequence delivers a reproducible synthetic model
pipeline and an experimental application integration. A qualified model release
still requires the research gates below. This distinction remains explicit in
`v0.2.0-alpha.1`; merging the preview does not certify the model.

Implemented:

- [x] dataset licensing, provenance, exclusions and grouped splits;
- [x] frozen generator benchmark, transparent metrics and CI regression gates;
- [x] optional CP-SAT baseline and governed room-graph preprocessing;
- [x] reproducible supervised CPU graph model and validation-selected checkpoint;
- [x] independent strict geometry, program, circulation and window validation;
- [x] bounded candidate expansion and pairwise distinct selection;
- [x] operator-enabled experimental engine, checkpoint integrity and tested fallback;
- [x] prospective development, validation, release and 1,000-brief stress protocol;
- [x] model card, failure evidence, reproduction commands and runtime packaging.

The [Phase 2F protocol](PHASE2F_PROTOCOL.md) defines the final engineering checks.
The [qualification report](../reports/phase2f-qualification.md) passes those checks:
five strict valid distinct plans for every 100-brief holdout and 1,000-brief stress
input, with observed warm p95 below one second on the measured runner.
The immutable Phase 2A–2E reports remain historical comparisons, including the
Phase 2E five-concept shortfall and the original room-area cost calculation.

Remaining model qualification, in priority order:

1. Demonstrate neural quality benefit against identical repair budgets and a
   strong solver reference. The current deterministic proposal/teacher family
   still limits topology diversity; more varied learned proposals need new
   development cohorts and a new locked holdout.
2. Admit an independently licensed real-plan source, validate its adapter and
   evaluate generalization. Unresolved Kaggle provenance/rights remain quarantined.
3. Collect blinded, consented preference judgments and meet the above-60% gate.
   Train a learned ranker only when appropriate ranking data exists; transparent
   metric ranking remains in this preview.
4. Promote the neural engine to default only after those gates pass. Until then,
   keep the deterministic engine available and report experimental fallback.

No external-data decision is required to use the synthetic preview. Source rights,
intended checkpoint distribution and the human evaluation protocol need review
before those later research steps begin.

[Phase 2G](PHASE2G_PROTOCOL.md) is delivered as `v0.2.0-alpha.2`: concept
conditioning reduces raw coordinate MAE by 35.89–36.55% against same-capacity
token ablation across three fixed training seeds. The concept/type reference and
adjacency-only solver still win on repaired adjacency and diversity. All raw
plans overlap, all repaired arms satisfy the five-concept contract, and the
reserved test remains unscored. See [the results](../reports/phase2g-conditioning.md).

The next model slice should inspect validation losses to the strong controls,
then prospectively test geometry-aware training or discrete slot prediction
under the same budgets. More diverse topology data and independent real-plan
evaluation remain necessary; lower raw MAE alone cannot justify promotion.
Phase 3 remains the next product track after this research increment.

## Phase 3 - Semantic 3D and BIM

- procedural wall, slab, door, window, and roof meshes;
- materials and browser first-person navigation;
- glTF export for web interchange;
- semantic quantities for a bill of materials;
- IFC export through IfcOpenShell with round-trip validation in a BIM viewer.

Exit condition: 2D edits regenerate consistent 3D and IFC representations.

## Phase 4 - Regional data and environmental analysis

- versioned jurisdiction rule packs with citations and effective dates;
- editable local cost catalog import rather than a mandatory paid API;
- site orientation and sun-path calculation;
- EnergyPlus integration for validated energy simulation;
- optional maps using license-compliant open geospatial resources.

Exit condition: every regional result exposes its source, date, assumptions, and
confidence boundary.

## Phase 5 - Immersive delivery

- WebXR walkthrough for compatible devices;
- performance budgets and reduced-detail modes;
- multi-user review only after privacy and authentication design;
- optional desktop packaging after the web workflow is stable.

Exit condition: the same semantic project model powers web, export, and immersive
views without duplicated state.
