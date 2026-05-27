# Soft Shell Calculator – UI

VIKTOR web application for analysing RPD (Resistance Pile Drilling) measurements of wooden foundation piles. Users upload `.rgp` measurement files bundled in zip archives and receive automated estimates of pile diameter, annual rings, sapwood width, and soft shell thickness.

## Features

- **Batch upload**: upload one or more zip archives containing `.rgp` files; multiple retaining walls per zip are supported.
- **Automated analysis**: signal processing and structural health estimation per pile (see `soft_shell_calculator_lib`).
- **Interactive views**: summary data view, pile-level result table, diameter histogram, and per-pile resistance + cross-section plots.
- **Validation tab**: exclude individual piles before export.
- **Export**: download a zip with CSV, JSON and HTML pile reports for all walls.

## Project structure

```
soft-shell-calculator-ui/
├── app.py                        VIKTOR entrypoint (thin re-export)
├── viktor.config.toml            VIKTOR app configuration
├── requirements.txt              Runtime dependencies
├── ui_app/                       Application package
│   ├── controller.py             View methods, download handler
│   ├── parametrization.py        Left-panel input fields (Dutch labels)
│   ├── view_models.py            Dataclasses for view layer
│   └── services/                 Business logic
│       ├── analysis_service.py   Orchestration: upload → domain model → view model
│       ├── export_service.py     CSV / JSON / HTML report generation
│       ├── plot_service.py       Plotly figure builders
│       └── upload_service.py     Zip extraction, file parsing, validation
├── soft_shell_calculator_lib/    Core calculation library (framework-agnostic)
└── tests/                        pytest test suite
```

## Prerequisites

- Python 3.12+
- A VIKTOR account and the `viktor-cli` installed ([docs.viktor.ai](https://docs.viktor.ai))

## Local development

```bash
cd soft-shell-calculator-ui

# Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
pip install -e .             # Install the lib in editable mode (if applicable)

# Run the app locally
viktor-cli start
```

## Running tests

From the repository root:

```bash
uv run pytest
```

## Configuration

| File | Purpose |
|------|---------|
| `viktor.config.toml` | App type (`editor`), Python version, registered name |
| `requirements.txt` | Pinned runtime dependencies deployed to VIKTOR |

## Usage workflow

1. Open the app in the VIKTOR platform.
2. **Invoer tab** – upload one or more zip archives with `.rgp` measurements.
3. Select a retaining wall and pile to inspect individual results.
4. **Validatie tab** – optionally exclude piles from the export.
5. **Resultaten tab** – download the full export (CSV + JSON + HTML per wall).