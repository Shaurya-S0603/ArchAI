# ArchAI v0.1.0-dev.1

This is the first public development preview of the complete Phase 1 architectural
editor. It is intentionally published from the `development` branch for review
before promotion to `main`.

## Included

- five deterministic residential layout directions;
- constrained move, resize, keyboard, and exact numeric room editing;
- semantic corridors, walls, doors, entries, and windows;
- furniture-use, door-approach, and accessible turning zones;
- preliminary planning feedback and local parametric cost estimates;
- SQLite project save, load, update, delete, and schema upgrades;
- interactive 2D/3D previews;
- JSON, SVG, PNG, vector PDF, OBJ, and print output;
- Pytest, Playwright, axe-core, and GitHub Actions quality gates.

## Verification target

- Python tests with at least 90% statement coverage;
- clean Ruff and JavaScript syntax checks;
- Chromium end-to-end coverage for the primary editor workflow;
- no automated axe violations across WCAG 2.0, 2.1, and 2.2 A/AA rule sets.

## Development boundaries

This release is for concept exploration and software evaluation. It is not a
trained AI model, BIM authoring tool, permit drawing, accessibility certification,
or substitute for a qualified architect or engineer.
