# ArchAI Web Architecture

## Decision

ArchAI v0.1 uses a Flask backend with a plain HTML, CSS, and JavaScript frontend.
This is a better base than Streamlit for the documented interaction model:

- drag-and-drop plan editing and undo/redo;
- a custom, responsive design interface;
- interactive 3D rendering in the browser;
- stable JSON APIs for future AI workers, mobile clients, or a desktop wrapper;
- SVG, JSON, and OBJ export without a proprietary component system.

Streamlit remains useful for research notebooks and model-evaluation dashboards,
but it is not the product shell.

The term "Java" is interpreted as **JavaScript**, because the requested browser UI
and the source documentation's React.js direction require JavaScript. There is no
JVM or Java runtime in the current architecture. If JVM Java is a separate course
or integration requirement, it should be added as an explicitly scoped service.

## Runtime topology

```mermaid
flowchart TD
    Browser["HTML/CSS/JavaScript client"] -->|JSON API| Flask["Flask application"]
    Flask --> Generator["Constraint layout generator"]
    Flask --> Checks["Preliminary rule checker"]
    Flask --> Cost["Parametric cost engine"]
    Flask --> Export["OBJ exporter"]
    Generator --> Browser
    Browser --> Local["JSON and SVG downloads"]
```

The application is stateless in v0.1. Project persistence, authentication, and a
database are intentionally deferred until the design schema is stable.

## Modules

| Module | Responsibility |
|---|---|
| `archai/models.py` | Validate the design brief and layout interchange schema |
| `services/layout_generator.py` | Generate five deterministic shape-partitioned layouts and adjacency metrics |
| `services/compliance.py` | Check area, boundaries, overlaps, adjacency, daylight potential, and review triggers |
| `services/cost_estimator.py` | Produce an editable concept-stage cost baseline |
| `services/exporter.py` | Convert concept floor geometry to Wavefront OBJ |
| `routes.py` | Serve the product UI and versioned API |
| `static/js/app.js` | Survey, SVG editor, history, analysis rendering, and exports |
| `static/js/viewer3d.js` | Dependency-free interactive 3D massing canvas |

## Free-resource policy

The executable uses only Python, Flask, browser-native APIs, and Gunicorn. It has
no paid API, cloud, font, analytics, or map dependency. Cost rates are local
assumptions and cannot be described as real-time market prices.

Recommended later open-source components:

- PyTorch for evaluated ML experiments;
- CubiCasa5K and other datasets only after license and provenance review;
- Blender for asset cleanup and visual QA;
- IfcOpenShell for IFC/BIM export;
- EnergyPlus for building-energy simulation;
- Leaflet plus an approved OpenStreetMap tile provider or self-hosted tiles;
- WebXR for browser VR.

## Safety boundary

ArchAI is an early-design assistant. A generated layout is not a permit drawing,
structural calculation, fire-safety certificate, accessibility certification, or
professional architectural service. Jurisdiction-specific rules must be versioned,
cited, tested, and reviewed by qualified professionals before release.
