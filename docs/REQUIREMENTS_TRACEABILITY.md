# Documentation-to-Implementation Traceability

This matrix separates what is executable now from what remains research or product
work. It prevents roadmap statements from being mistaken for shipped capability.

| Documented capability | v0.1 development status | Evidence / next step |
|---|---|---|
| Structured design survey | Working | Browser form plus `DesignBrief` validation |
| Five optimized layout concepts | Working baseline | Deterministic corridor/perimeter partition generation and adjacency scoring; ML is not yet used |
| Graph/shape-grammar planning | Partial | Corridor partitioning, room adjacency, and connected door graphs are implemented |
| Drag-and-drop editing | Partial | Rooms can be moved and resized; wall/opening topology rebuilds after each edit; keyboard movement works |
| Non-drag room editing | Working | Exact numeric position/dimension editor plus keyboard room movement |
| Undo/redo | Working | Per-concept room-history stack in the browser |
| Project persistence | Working | Migrated SQLite schema plus validated save/list/load/update/delete APIs and browser controls |
| Corridors, walls, doors, and windows | Working baseline | Explicit corridor rooms and deterministic semantic topology are rendered and exported |
| Furniture and accessibility zones | Working baseline | Deterministic furniture-use, door-approach, and 1.5 m turning-circle overlays are derived from plan geometry |
| Generic compliance feedback | Working baseline | Area, bounds, overlap, adjacency, daylight potential, and review triggers |
| Jurisdiction-specific certification | Not implemented | Requires sourced and versioned rule packs plus professional review |
| Cost estimate and budget comparison | Working baseline | Local parametric rates; no claim of live supplier data |
| Interactive 3D model | Partial | Orbitable browser massing preview; semantic openings are still limited to the 2D plan |
| JSON/SVG/PNG/PDF/OBJ export | Working | Browser downloads, browser-native PNG rasterization, and Python OBJ/PDF endpoints |
| IFC/BIM export | Not implemented | Add a semantic building model and IfcOpenShell exporter |
| Trained neural/RL generator | Not implemented | Establish dataset licenses, evaluation set, baseline metrics, and reproducible training first |
| Site/sun/wind analysis | Not implemented | Add geospatial input and verified environmental model |
| VR/AR walkthrough | Not implemented | Build WebXR experience after stable 3D semantic geometry |
| Structural integrity verification | Not implemented | Keep outside automated claims without a validated engineering integration |
| WCAG 2.2 A/AA quality gate | Working baseline | Keyboard and focus review plus automated axe checks in Chromium; manual assistive-technology testing remains advisable |

## Documentation correction

The research paper's compliance table states a `70 m²` bedroom minimum, while its
technical constraints specify a bedroom minimum of `3 m × 3 m`. The MVP uses the
internally consistent `9 m²` preliminary rule and identifies it as an editable MVP
rule—not a universal building-code requirement.
