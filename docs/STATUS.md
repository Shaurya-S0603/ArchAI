# ArchAI - Project Status

**Last updated:** August 31, 2026

**Release branch:** `main`

**Current milestone:** Phase 0 - Executable web foundation

## Overall status

ArchAI has been reconfigured from a documentation-only Unity concept into a
working, web-first application using Python, Flask, HTML, CSS, and JavaScript.
The current milestone is a truthful MVP baseline, not the complete trained AI,
BIM, code-certification, or VR product described in the research plan.

**Project health:** green for Phase 0, research-stage for later phases.

## Implemented

- Flask application factory, production WSGI entrypoint, and versioned JSON API;
- validated residential design survey;
- five deterministic shape-partitioned layout concepts;
- room adjacency graph and ranking metrics;
- generic preliminary rule checks with clear professional-review boundaries;
- parametric local cost baseline and budget comparison;
- editable SVG plan with pointer/keyboard movement and undo/redo;
- interactive browser 3D massing preview;
- JSON, SVG, and OBJ exports;
- Windows and Unix launchers, Dockerfile, and free Render blueprint;
- automated Python tests and lint configuration;
- architecture, traceability, roadmap, and corrected model documentation.

## Verification

- 9 backend tests passing;
- 93% Python statement coverage at this milestone;
- Python lint clean;
- all JavaScript modules pass syntax checks;
- Flask development and Gunicorn production entrypoints respond successfully.

## Next milestone

Phase 1 will turn rectangular concepts into a real architectural editor:

1. explicit walls, openings, doors, windows, and circulation zones;
2. resize handles with topology-preserving constraints;
3. SQLite project persistence and schema migration;
4. printable plan sheets plus PNG/PDF export;
5. browser end-to-end tests and a WCAG 2.2 AA accessibility audit.

The trained generator begins only after a licensed data pipeline and held-out
evaluation framework are established. See `docs/ROADMAP.md` and
`docs/REQUIREMENTS_TRACEABILITY.md`.
