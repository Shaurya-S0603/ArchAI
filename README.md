# ArchAI - Architectural Concept Design Studio

ArchAI is a free and open-source architectural concept application that turns a
residential design brief into five editable 2D layout directions. It provides
transparent preliminary planning checks, an editable cost baseline, an interactive
3D massing preview, and JSON/SVG/OBJ export.

> **Current release:** executable web MVP. It is not yet the trained AI, BIM,
> jurisdictional compliance, or VR system described by the long-term research plan.
> See the [traceability matrix](docs/REQUIREMENTS_TRACEABILITY.md) for the exact
> implementation boundary.

## Phase 0 release

| Item | Status |
|---|---|
| Release | `v0.1.0 - Phase 0` |
| Application | Executable Flask web MVP |
| Cost | No paid API or runtime dependency |
| Deployment | Local, Docker, or free-tier Render |
| License | MIT |
| Safety boundary | Preliminary concepts only; not for construction |

## Working features

- validated survey for site, household, rooms, style, and budget;
- five deterministic layout concepts ranked by adjacency and compactness;
- draggable SVG rooms, keyboard movement, undo, and redo;
- preliminary checks for dimensions, overlaps, bounds, connectivity, functional
  adjacency, daylight potential, and large-plan egress review;
- local parametric cost estimate with a budget comparison;
- dependency-free orbitable 3D concept massing;
- JSON, SVG, and Wavefront OBJ downloads;
- responsive, keyboard-accessible interface;
- testable Flask API and Docker deployment.

ArchAI assists early exploration only. A qualified architect or engineer must
verify any design used for permitting, procurement, or construction.

## Technology

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ and Flask 3 |
| Frontend | Semantic HTML, custom CSS, browser-native JavaScript |
| 2D | SVG |
| 3D | Browser Canvas 2D isometric massing renderer |
| Production server | Gunicorn |
| Tests | Pytest |
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
```

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
| `POST` | `/api/v1/layouts/generate` | Validate a brief and generate five analyzed concepts |
| `POST` | `/api/v1/layouts/analyze` | Recheck an edited concept |
| `POST` | `/api/v1/exports/obj` | Export room massing as OBJ |

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Delivery roadmap](docs/ROADMAP.md)
- [Current project status](docs/STATUS.md)
- [Generator model card](docs/MODEL_CARD.md)
- [Contribution guide](CONTRIBUTING.md)

## License

See [LICENSE](LICENSE). Dataset and model licenses must be reviewed separately
before any training artifact is redistributed.

Maintained by Shaurya Singhal.
