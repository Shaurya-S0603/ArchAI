# Documentation-to-Implementation Traceability

This matrix separates what is executable now from what remains research or product
work. It prevents roadmap statements from being mistaken for shipped capability.

| Documented capability | v0.1 status | Evidence / next step |
|---|---|---|
| Structured design survey | Working | Browser form plus `DesignBrief` validation |
| Five optimized layout concepts | Working baseline | Deterministic partition generation and adjacency scoring; ML is not yet used |
| Graph/shape-grammar planning | Partial | Shape partitioning and an explicit adjacency graph are implemented |
| Drag-and-drop editing | Partial | Rooms can be moved with pointer or keyboard; resizing and topology repair are next |
| Undo/redo | Working | Per-concept room-history stack in the browser |
| Generic compliance feedback | Working baseline | Area, bounds, overlap, adjacency, daylight potential, and review triggers |
| Jurisdiction-specific certification | Not implemented | Requires sourced and versioned rule packs plus professional review |
| Cost estimate and budget comparison | Working baseline | Local parametric rates; no claim of live supplier data |
| Interactive 3D model | Partial | Orbitable browser massing preview; doors, furniture, materials, and first-person mode remain |
| JSON/SVG/OBJ export | Working | Browser downloads and Python OBJ endpoint |
| PNG/PDF export | Not implemented | Add print layout and rasterization in the export milestone |
| IFC/BIM export | Not implemented | Add a semantic building model and IfcOpenShell exporter |
| Trained neural/RL generator | Not implemented | Establish dataset licenses, evaluation set, baseline metrics, and reproducible training first |
| Site/sun/wind analysis | Not implemented | Add geospatial input and verified environmental model |
| VR/AR walkthrough | Not implemented | Build WebXR experience after stable 3D semantic geometry |
| Structural integrity verification | Not implemented | Keep outside automated claims without a validated engineering integration |

## Documentation correction

The research paper's compliance table states a `70 m²` bedroom minimum, while its
technical constraints specify a bedroom minimum of `3 m × 3 m`. The MVP uses the
internally consistent `9 m²` preliminary rule and identifies it as an editable MVP
rule—not a universal building-code requirement.
