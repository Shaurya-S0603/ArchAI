# ArchAI Delivery Roadmap

## Phase 0 - Executable web foundation (current)

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

- room resizing with handles and minimum-dimension constraints;
- explicit corridors, doors, windows, wall segments, and openings;
- topology repair after edits;
- furniture zones and accessibility clearances;
- project persistence in SQLite with schema migrations;
- printable plan sheets and PNG/PDF export;
- end-to-end browser tests and WCAG 2.2 AA audit.

Exit condition: a saved project can be edited, reloaded, printed, and exported
without geometry corruption.

## Phase 2 - Evaluated generative intelligence

- document dataset licenses, provenance, exclusions, and splits;
- establish heuristic and constraint-solver baselines;
- define validity, adjacency, diversity, and user-alignment metrics;
- train a model only when it beats the baseline on a held-out evaluation set;
- publish reproducible training scripts, checkpoints, model card, and failure cases;
- keep the deterministic generator as a no-GPU fallback.

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
