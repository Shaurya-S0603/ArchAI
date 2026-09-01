# ArchAI - Project Status

**Last updated:** September 1, 2026

**Release branch:** `development` (draft review into `main`)

**Current milestone:** Phase 1 complete - v0.1 development preview

## Overall status

ArchAI now supports local project persistence, constrained room resizing, semantic
plan topology, deterministic furniture/accessibility zones, and printable plan
output while retaining the Python, Flask, HTML, CSS, and JavaScript stack.
The development preview is an editor release, not the complete trained AI,
BIM, code-certification, or VR product described in the research plan.

**Project health:** green for Phase 1, research-stage for later phases.

## Implemented

- Flask application factory, production WSGI entrypoint, and versioned JSON API;
- validated residential design survey;
- five deterministic corridor/perimeter layout concepts;
- room adjacency graph and ranking metrics;
- generic preliminary rule checks with clear professional-review boundaries;
- parametric local cost baseline and budget comparison;
- editable SVG plan with pointer/keyboard movement and undo/redo;
- interactive browser 3D massing preview;
- JSON, SVG, PNG, vector PDF, and OBJ exports plus browser printing;
- Windows and Unix launchers, Dockerfile, and free Render blueprint;
- automated Python tests and lint configuration;
- architecture, traceability, roadmap, and corrected model documentation.

## Phase 1A implemented

- SQLite project store with a forward-only migration ledger;
- save, list, load, update, and delete project API routes;
- server-side schema validation plus compliance and cost recomputation on save;
- browser project library with accessible status feedback;
- four corner resize handles with grid snapping, footprint bounds, minimum room
  dimensions, and room-type minimum areas;
- undo/redo support for move and resize operations.

## Phase 1B implemented

- one continuous 1.8 m corridor spine in every generated concept;
- perimeter room strips that preserve minimum dimensions and corridor access;
- deterministic deduplicated exterior, interior, and exposed-boundary walls;
- a connected spanning set of interior doors plus one exterior entry door;
- exterior windows for every generated habitable room;
- automatic wall/opening rebuilding after geometry edits;
- topology-aware compliance and accessibility door-width feedback;
- semantic topology in JSON persistence and SVG exports;
- automatic schema v1 to schema v2 project upgrades on load.

## Phase 1C implemented

- deterministic furniture-use zones for supported room types;
- door-approach clearances derived from semantic openings;
- 1.5 m turning-circle overlays for accessible bathrooms and circulation space;
- automatic zoning rebuilding after generation, editing, analysis, save, and load;
- schema v3 project snapshots with automatic upgrades from schemas v1 and v2;
- browser-native PNG downloads and print-specific page styling;
- vector A3 landscape PDF plan sheets with title block, scale, north arrow,
  planning checks, and a professional-review disclaimer;
- free, local PDF generation with the BSD-licensed ReportLab toolkit.

## Phase 1D quality gate implemented

- exact numeric room editing as a no-drag alternative;
- keyboard-operated concept tabs, room selection, movement, focus treatment, and
  skip navigation;
- minimum interactive target sizing and focus-obscuring safeguards;
- serial Playwright coverage for generation, editing, undo, 3D switching,
  persistence, reload, and PDF export;
- automated axe checks for WCAG 2.0, 2.1, and 2.2 A/AA rules in initial and
  generated interface states;
- GitHub Actions jobs for Python quality and Chromium browser quality.

## Verification

- 21 backend tests passing with 92% Python statement coverage;
- Python lint clean;
- all JavaScript modules pass syntax checks;
- Flask development and Gunicorn production entrypoints respond successfully.
- browser tests and accessibility checks run locally and on the development CI workflow.

## Next milestone

Phase 2 begins with licensed-data provenance, evaluation metrics, and transparent
baseline comparisons before any trained generator is shipped.

The trained generator begins only after a licensed data pipeline and held-out
evaluation framework are established. See `docs/ROADMAP.md` and
`docs/REQUIREMENTS_TRACEABILITY.md`.
