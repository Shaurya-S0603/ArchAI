# Contributing to ArchAI

Thank you for helping build ArchAI. The v0.2 development preview is a
Python/Flask application with a browser-native HTML, CSS, and JavaScript frontend.

## Development setup

Requirements:

- Python 3.11 or newer;
- Node.js 20 or newer for browser quality checks;
- Git;
- a modern browser;
- Docker only when testing the container build.

```bash
git clone https://github.com/Shaurya-S0603/ArchAI.git
cd ArchAI
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
npm ci
npx playwright install chromium
python app.py
```

Open `http://127.0.0.1:5000`.

## Before opening a pull request

```bash
pytest
ruff format --check .
ruff check .
node --check archai/static/js/app.js
npm run test:e2e
python -m archai.evaluation --enforce
```

All tests and checks must pass. Add tests whenever backend behavior changes.
For UI work, add or update Playwright coverage and verify keyboard navigation,
visible focus, narrow-screen layout, reduced-motion behavior, and the axe A/AA
audit in both initial and generated interface states.
Changes to generation, topology, zoning, or compliance must also pass the full
100-case benchmark. Include fresh JSON and Markdown reports when deliberately
changing a frozen metric or threshold.

## Branches and commits

Use a short branch name such as:

- `feature/room-resizing`
- `fix/obj-export-groups`
- `docs/cost-assumptions`

Prefer Conventional Commit messages:

- `feat: add room resize handles`
- `fix: prevent overlapping room export`
- `docs: clarify compliance limitations`
- `test: cover invalid layout requests`

## Architecture rules

- Keep domain logic in `archai/services/`, not Flask route functions.
- Validate untrusted API data through the domain models.
- Keep the deterministic no-GPU generator available as a fallback.
- Do not describe preliminary checks as regulatory certification.
- Do not add paid APIs or proprietary runtime dependencies to the default build.
- Document the source, license, date, and assumptions for every dataset or
  regional rule pack.
- Version benchmark data instead of mutating an existing dataset release.
- Evaluate candidate generators through the shared `DesignBrief -> list[Layout]`
  interface and keep hard constraints outside learned components.
- Never commit credentials, personal data, generated virtual environments, or
  large model checkpoints.

## Scope

Check [the roadmap](docs/ROADMAP.md) and
[requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md) before starting a
large feature. Open an issue first when a change affects the project schema,
model-training approach, compliance claims, or export compatibility.

By contributing, you agree that your contribution is provided under the
[MIT License](LICENSE).
