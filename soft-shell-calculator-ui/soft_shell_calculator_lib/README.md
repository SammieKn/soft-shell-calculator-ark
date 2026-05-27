# soft-shell-calculator-lib

Backend library for analyzing RPD (Resistograph Pile Drilling) measurements of wooden foundation piles. Framework-agnostic — no UI dependency. Can be used standalone in scripts, notebooks, or as a dependency of a web application.

## Installation

```bash
pip install .
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install .
```

## Quick Start

```python
from pathlib import Path
from soft_shell_calculator_lib import RetainingWall

wall = RetainingWall.from_directory(Path("path/to/rgp_files"))

for part in wall.construction_parts:
    for pile in part.wooden_piles:
        print(f"{pile.id}: diameter={pile.diameter:.1f} mm, "
              f"soft shell={pile.soft_shell_entrance_thickness:.1f} mm")
```

## Package Layout

```
soft_shell_calculator_lib/
├── __init__.py            Public API exports
├── py.typed               PEP 561 type-hint marker
├── constants.py           Algorithm constants (no magic numbers elsewhere)
├── utils.py               Logger setup, filename parsing, measurement pairing
├── calculator.py          Pure signal processing and calculation functions
└── models/
    ├── __init__.py        Re-exports all model classes
    ├── rpd_measurement.py RPDMeasurement — one .rgp file
    ├── wooden_pile.py     WoodenPile — one pile with its measurements
    ├── construction_part.py ConstructionPart — a group of piles
    └── retaining_wall.py  RetainingWall — top-level domain object
```

## Domain Model

The domain hierarchy mirrors a physical foundation inspection:

```
RetainingWall
└── ConstructionPart (one or more)
    └── WoodenPile (one or more)
        └── RPDMeasurement (one or two per pile — one drill pass per side)
```

A `WoodenPile` normally has two `RPDMeasurement` objects from opposite sides. Results are averaged across both passes.

## Public API

All public symbols are importable directly from `soft_shell_calculator_lib`:

| Symbol | Description |
|--------|-------------|
| `RetainingWall` | Top-level model; load from a directory of `.rgp` files |
| `ConstructionPart` | Group of piles within a wall |
| `WoodenPile` | Single pile with computed properties (diameter, rings, sapwood, soft shell) |
| `RPDMeasurement` | Single `.rgp` file parsed into structured data |
| `MeasurementIdentifier` | Parsed filename/ID components |
| `pair_measurements` | Utility to pair filename stems by pile |

## Calculation Pipeline

Each `RPDMeasurement` is processed through the following steps (implemented in `calculator.py`):

1. **Filter signal** — remove near-zero samples before the drill enters wood
2. **Trim signal** — variance-based trimming to isolate the wood cross-section
3. **Estimate diameter** — from the length of the trimmed signal
4. **Moving average** — symmetric 100-sample smoothing
5. **Count annual rings** — Savitzky-Golay smoothing + peak detection
6. **Estimate growth rate** — peak spacing in the outer 75% zone
7. **Estimate sapwood width** — empirical regression formula
8. **Detect soft shell** — IOMA (Incremental One-directional Moving Average) threshold

## Units

All spatial values use **millimetres (mm)**, matching the `.rgp` file format (`resolutionFeed` in samples/mm).

## Dependencies

- `numpy >= 1.26.0`
- `scipy >= 1.11.0`

No other runtime dependencies.
