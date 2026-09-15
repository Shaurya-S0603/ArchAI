# ArchAI - Architectural Concept Design Studio

ArchAI is a free and open-source architectural concept application that turns a
residential design brief into five editable 2D layout directions. It provides
transparent preliminary planning checks, an editable cost baseline, an interactive
3D massing preview, and JSON/SVG/PNG/PDF/OBJ export.

> **Current development preview:** `v0.2.0-alpha.2`, adding the Phase 2G
> concept-conditioning experiment to the Phase 2A–2F engineering alpha.
> Raw prediction improves across three seeds; downstream neural superiority,
> independent real-plan evaluation and human-preference qualification remain open.
> See the [traceability matrix](docs/REQUIREMENTS_TRACEABILITY.md) for the exact
> implementation boundary.

## Development release

| Item | Status |
|---|---|
| Release | `v0.2.0-alpha.2 - Phase 2G research preview` |
| Application | Executable Flask editor with benchmarked baseline and solver candidate |
| Cost | No paid API or runtime dependency |
| Deployment | Local, Docker, or free-tier Render |
| License | MIT |
| Safety boundary | Preliminary concepts only; not for construction |

## Model development

| Milestone | Delivered | Evidence |
|---|---|---|
| Phase 1 | Persistent, editable 2D/3D plans, topology, zoning, exports and browser accessibility checks | [Changelog](CHANGELOG.md) |
| Phase 2A | Frozen 100-brief generator benchmark and CI regression gates | [Baseline](reports/phase2a-baseline.md) |
| Phase 2B | Optional CP-SAT generator and reviewed dataset candidate register | [Comparison](reports/phase2b-comparison.md) |
| Phase 2C | Governed room graphs, deduplication, splits and 592-plan synthetic pilot | [Data contract](docs/TRAINING_DATA_PIPELINE.md) |
| Phase 2D | Reproducible supervised CPU graph model and held-out evaluation | [Experiment](reports/phase2d-baseline.md) |
| Phase 2E | Strict proposal repair, distinct-concept selection and matched evaluation | [Repair report](reports/phase2e-repair.md) |
| Phase 2F | Bounded diverse search, experimental serving/fallback and fresh qualification | [Protocol](docs/PHASE2F_PROTOCOL.md) |
| Phase 2G | Concept conditioning, fresh grouped data and three-seed matched comparison | [Results](reports/phase2g-conditioning.md) |

Phase 2F expands repaired proposals into five pairwise distinct concepts within
ArchAI's supported corridor layout family. Every experimental response passes
independent geometry, room-program, circulation and duplicate checks. The default
application continues to use the deterministic generator; an operator can enable
the frozen neural engine with an automatic, observable fallback.

Use the [training guide](docs/LEARNED_BASELINE.md) to reproduce the checkpoint and
[Phase 2F protocol](docs/PHASE2F_PROTOCOL.md) for qualification and serving setup.
PyTorch and OR-Tools are optional; no paid service is required. External datasets
remain pending source admission. A qualified model release also requires real-plan
validation, human preference evidence and demonstrated neural quality benefit.

The [Phase 2F qualification report](reports/phase2f-qualification.md) records
five strict valid distinct concepts for every one of 100 held-out briefs and
1,000 stress briefs. Holdout adjacency is 99.14% versus 65.36% for the baseline;
observed warm CPU p95 is 0.799 seconds on the measured runner.

The [Phase 2G experiment](reports/phase2g-conditioning.md) reduces raw validation
coordinate error by 35.89–36.55% against a same-capacity token ablation. All four
arms return five valid, distinct plans on the same 32 validation briefs across
three seeds. The conditioned model still trails simpler controls after repair;
its checkpoint remains offline, and the 100-brief reserved test is unscored.

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
- local parametric cost estimate for the complete building footprint, with a budget comparison;
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
| Evaluation | Versioned JSONL benchmark and standard-library Python harness |
| Optional learned model | PyTorch CPU graph regressor and constrained proposal repair |
| Optional solver | OR-Tools CP-SAT 9.15 (research/evaluation extra) |
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
python -m archai.evaluation --enforce
python -m archai.evaluation.comparison --enforce
```

The browser suite starts its own local Flask server, exercises the complete
generate/edit/save/load/export workflow, and checks initial and generated states
for automated WCAG 2.2 A/AA violations.

The generator benchmark evaluates the committed 100-case dataset and returns a
non-zero exit code if a required quality threshold regresses. To save fresh reports without overwriting the frozen evidence:

```bash
python -m archai.evaluation --enforce \
  --json benchmark-artifacts/baseline.json \
  --markdown benchmark-artifacts/baseline.md
python -m archai.evaluation.comparison --enforce \
  --json solver-artifacts/comparison.json \
  --markdown solver-artifacts/comparison.md
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

- [Release changelog](CHANGELOG.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Delivery roadmap](docs/ROADMAP.md)
- [Current project status](docs/STATUS.md)
- [Accessibility audit](docs/ACCESSIBILITY_AUDIT.md)
- [Dataset governance](docs/DATASET_GOVERNANCE.md)
- [External dataset candidate register](docs/DATASET_CANDIDATES.md)
- [Evaluation protocol](docs/EVALUATION_PROTOCOL.md)
- [Phase 2F qualification and experimental serving](docs/PHASE2F_PROTOCOL.md)
- [Phase 2G concept-conditioning protocol](docs/PHASE2G_PROTOCOL.md)
- [Constraint repair and reproduction](docs/CONSTRAINT_REPAIR.md)
- [Learned baseline and reproduction](docs/LEARNED_BASELINE.md)
- [Generator model card](docs/MODEL_CARD.md)
- [Contribution guide](CONTRIBUTING.md)

## License

See [LICENSE](LICENSE). Dataset and model licenses must be reviewed separately
before any training artifact is redistributed.

Maintained by Shaurya Singhal.
