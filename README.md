# ArchAI - Architectural Concept Design Studio

ArchAI is a free and open-source architectural concept application that turns a
residential design brief into five editable 2D layout directions. It provides
transparent preliminary planning checks, an editable cost baseline, an interactive
3D massing preview, and JSON/SVG/PNG/PDF/OBJ export.

> **Current development preview:** `v0.1.0-dev.1`, completing the Phase 1
> architectural editor. It is not yet the trained AI, BIM,
> jurisdictional compliance, or VR system described by the long-term research plan.
> See the [traceability matrix](docs/REQUIREMENTS_TRACEABILITY.md) for the exact
> implementation boundary.

## Development release

| Item | Status |
|---|---|
| Release | `v0.1.0-dev.1 - Phase 1 complete` |
| Application | Executable Flask architectural editor |
| Cost | No paid API or runtime dependency |
| Deployment | Local, Docker, or free-tier Render |
| License | MIT |
| Safety boundary | Preliminary concepts only; not for construction |

## Phase 1 delivery

- local SQLite project library with forward-only schema migrations;
- validated save, list, load, update, and delete project APIs;
- four-corner room resizing with 0.25 m snapping, footprint limits, a 1.8 m
  minimum dimension, and room-type minimum areas;
- saved projects retain the brief, all five concepts, the selected concept,
  analysis, and cost state;
- server-side revalidation and recalculation before project data is stored.
- continuous corridor spines with perimeter room strips;
- deduplicated exterior, interior, and exposed room-boundary wall segments;
- connected interior doors, an exterior entry door, and habitable-room windows;
- automatic topology rebuilding after every move, resize, save, and legacy-project load;
- deterministic furniture-use, door-approach, and accessibility turning zones;
- browser PNG export, printable plan views, and vector A3 PDF plan sheets;
- schema v3 project snapshots with automatic in-memory upgrade from schemas v1 and v2;
- no-drag numeric room editing and keyboard-operable concept tabs;
- Playwright end-to-end coverage and automated axe WCAG 2.2 A/AA checks in CI.

## Working features

- validated survey for site, household, rooms, style, and budget;
- five deterministic layout concepts ranked by adjacency and compactness;
- draggable and resizable SVG rooms, an exact no-drag editor, keyboard movement,
  undo, and redo;
- persistent local projects backed by SQLite;
- semantic walls, doors, windows, openings, and explicit corridor space;
- furniture-use and accessibility clearance overlays;
- preliminary checks for dimensions, overlaps, bounds, connectivity, functional
  adjacency, daylight potential, and large-plan egress review;
- local parametric cost estimate with a budget comparison;
- dependency-free orbitable 3D concept massing;
- JSON, SVG, PNG, vector PDF, and Wavefront OBJ downloads plus browser printing;
- responsive, keyboard-accessible interface;
- testable Flask API and Docker deployment.

ArchAI assists early exploration only. A qualified architect or engineer must
verify any design used for permitting, procurement, or construction.

## Technology

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ and Flask 3 |
| Persistence | SQLite with built-in schema migrations |
| Frontend | Semantic HTML, custom CSS, browser-native JavaScript |
| 2D | SVG |
| 3D | Browser Canvas 2D isometric massing renderer |
| Plan sheets | ReportLab vector PDF generation |
| Production server | Gunicorn |
| Tests | Pytest, Playwright, and axe-core |
| Packaging | Local virtual environment or Docker |

"Java" is interpreted as **JavaScript** for this web project. The current
architecture does not require a Java/JVM service. The rationale is recorded in
[the architecture decision](docs/ARCHITECTURE.md).

## Run locally

### Windows

1. Install Python 3.11 or newer.
2. Double-click `run.bat`, or run it from Command Prompt:

   ```bat
   run.bat
   ```

3. Open `http://127.0.0.1:5000`.

The launcher creates `.venv` and installs the requirements on its first run.

### macOS or Linux

```bash
chmod +x run.sh
./run.sh
```

Then open `http://127.0.0.1:5000`.

### Manual development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python app.py
```

## Test and lint

```bash
pytest
ruff check .
npm ci
npx playwright install chromium
npm run test:e2e
```

The browser suite starts its own local Flask server, exercises the complete
generate/edit/save/load/export workflow, and checks initial and generated states
for automated WCAG 2.2 A/AA violations.

## Docker

```bash
docker build -t archai .
docker run --rm -p 10000:10000 archai
```

Open `http://127.0.0.1:10000`.

## Free web deployment

The included `render.yaml` can deploy the Docker app as a free Render web service.
Render's free service is suitable for hobby demos and may spin down when idle. No
paid API is required by ArchAI. You can also deploy the Flask application to the
limited free PythonAnywhere tier.

- [Render free service documentation](https://render.com/docs/free)
- [PythonAnywhere Flask setup](https://help.pythonanywhere.com/pages/Flask/)
- [Flask deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/)

Free-tier terms can change, so verify the provider's current limits before
deployment and do not add a payment method unless you intentionally want billing.

## API

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Deployment health check |
| `POST` | `/api/v1/layouts/generate` | Generate five analyzed concepts with semantic topology |
| `POST` | `/api/v1/layouts/analyze` | Rebuild topology and recheck an edited concept |
| `POST` | `/api/v1/exports/obj` | Export room massing as OBJ |
| `POST` | `/api/v1/exports/pdf` | Export an A3 vector concept plan sheet as PDF |
| `GET`, `POST` | `/api/v1/projects` | List or create saved projects |
| `GET`, `PUT`, `DELETE` | `/api/v1/projects/{id}` | Load, update, or delete a project |

Projects are stored by default in `instance/archai.sqlite3`. Set
`ARCHAI_DATABASE` to an explicit writable path when deploying with persistent
storage. Hosts with ephemeral filesystems will not retain SQLite data across
service replacement or redeployment.

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Delivery roadmap](docs/ROADMAP.md)
- [Current project status](docs/STATUS.md)
- [Accessibility audit](docs/ACCESSIBILITY_AUDIT.md)
- [v0.1 development release notes](docs/RELEASE_NOTES_v0.1.0-dev.1.md)
- [Generator model card](docs/MODEL_CARD.md)
- [Contribution guide](CONTRIBUTING.md)

## License

See [LICENSE](LICENSE). Dataset and model licenses must be reviewed separately
before any training artifact is redistributed.

Maintained by Shaurya Singhal.
