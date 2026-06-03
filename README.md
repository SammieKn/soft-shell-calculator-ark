# Soft Shell Calculator

## Description

The Soft Shell Calculator analyzes RPD (Resistance Pile Drilling) measurements of wooden foundation piles to estimate the structural health of the wood cross-section. It produces estimates for the pile diameter, number of annual growth rings, sapwood width, and soft shell thickness. These outputs are used by Gemeente Amsterdam to assess decay in wooden foundation piles without destructive sampling.

## Repository structure

This is a monorepo containing three packages:

```
soft-shell-calculator-ark/
├── data/                           Sample .rgp measurement files for development and testing
├── soft-shell-calculator-ui/       VIKTOR web application (user interface + library)
│   ├── ui_app/                     Application layer (controller, views, services)
│   └── soft_shell_calculator_lib/  Core calculation library (framework-agnostic)
└── soft-shell-calculator-tudelft/  Original TU Delft script, preserved as reference
```

### `soft-shell-calculator-ui`

The production application, built on the [VIKTOR](https://viktor.ai) platform. Users upload zip archives with `.rgp` measurements and receive automated analysis, interactive visualisations, and downloadable reports. Contains the `soft_shell_calculator_lib` package which holds all domain models and signal processing logic.

See [`soft-shell-calculator-ui/README.md`](./soft-shell-calculator-ui/README.md) for setup, development and usage instructions.

### `soft_shell_calculator_lib`

The core calculation library, embedded within `soft-shell-calculator-ui/`. Framework-agnostic; no UI dependency. Responsible for:

- Loading and parsing `.rgp` measurement files
- Domain models (`RPDMeasurement`, `WoodenPile`, `ConstructionPart`, `RetainingWall`)
- Signal processing and calculations (filtering, ring counting, sapwood and soft shell estimation)

See [`soft_shell_calculator_lib/README.md`](./soft-shell-calculator-ui/soft_shell_calculator_lib/README.md) for the module layout and API.

### `soft-shell-calculator-tudelft`

The original wxPython desktop application developed by TU Delft (v1.1, Anindya and Michele Mirra). Preserved unchanged as the reference implementation. The algorithms and domain knowledge in this script form the basis for the refactored library.

See [`soft-shell-calculator-tudelft/README.md`](./soft-shell-calculator-tudelft/README.md) for installation and usage.

## Getting started

All Python dependencies are managed by the root `pyproject.toml` via [uv](https://docs.astral.sh/uv/).

### Run the VIKTOR app

```bash
cd soft-shell-calculator-ui
pip install -r requirements.txt   # into a venv for viktor-cli
viktor-cli start
```

### Run tests

```bash
uv run pytest
```

### Run the TU Delft desktop app

```bash
uv run --extra tudelft python soft-shell-calculator-tudelft/main.py
```

## Source recognition

This application is built on the original code and algorithms developed by TU Delft in collaboration with Gemeente Amsterdam.
The original implementation can be found in [`soft-shell-calculator-tudelft/`](./soft-shell-calculator-tudelft/).