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

## Phase 2 - Evaluated generative intelligence

- [x] document dataset licenses, provenance, exclusions, and splits;
- [x] freeze a deterministic 100-case synthetic benchmark with integrity checks;
- [x] establish and enforce the transparent heuristic baseline;
- [x] define validity, adjacency, diversity, budget, accessibility, and
  user-alignment metrics;
- [x] implement and benchmark an open-source constraint-solver candidate;
- [x] add a governed rectangular-plan preprocessing and training-data interface;
- [ ] admit an external real-plan source and validate its source-specific adapter;
- [x] implement and train an offline graph-conditioned learned baseline;
- [ ] qualify a repaired learned candidate for product integration;
- [x] add deterministic constraint repair and candidate diversity selection;
- [ ] satisfy the five-concept contract with at least four distinct valid concepts;
- [ ] train and validate a learned ranker;
- promote a trained model only when it beats the baseline on a held-out evaluation set;
- publish reproducible training scripts, checkpoints, model card, and failure cases;
- keep the deterministic generator as a no-GPU fallback.

Current development release: `v0.2.0-dev.5` completes Phase 2E's restricted
repair component. All 100 benchmark briefs produce strictly valid repair; 79%
return four distinct concepts and 72% return five. The matched reference has
slightly higher adjacency, so the complete learned generator remains unqualified.
See [repair evidence](../reports/phase2e-repair.md).

Next slice, Phase 2F, in priority order:

1. Create new development/validation briefs before improving the search for diverse
   templates and proposals. Keep strict repair and duplicate rejection mandatory.
2. Establish a neural benefit using identical repair budgets for learned and
   train-only reference proposals; improve beyond the restricted teacher family.
3. Meet the five-result and diversity gates on a new locked holdout, then repeat
   end-to-end CPU latency and 1,000-brief stress evaluation.
4. Admit an independently licensed real-plan source and arrange blinded preference
   evaluation before application/fallback integration. External sources with
   unresolved rights remain quarantined.

Exit condition: the trained generator is measurably better than the transparent
baseline and never bypasses hard constraints.

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
