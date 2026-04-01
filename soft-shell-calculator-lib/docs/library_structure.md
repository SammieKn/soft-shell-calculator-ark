# Library Structure — soft-shell-calculator-lib

This document describes the intended structure of the `soft-shell-calculator-lib` package, the responsibility of each module, and where specific logic should live.

---

## Purpose

`soft-shell-calculator-lib` is the backend library for the soft shell calculator. It is framework-agnostic and has no dependency on any UI. It is consumed by `soft-shell-calculator-ui` (the Viktor frontend) and can be used independently in scripts or notebooks.

The library is responsible for:
- Representing the domain objects (data models)
- Loading `.rgp` measurement files
- Running the signal processing and calculations
- Providing utility functions shared across modules

---

## Package layout

```
soft-shell-calculator-lib/
├── pyproject.toml                          Project metadata and dependencies
├── docs/
│   ├── library_structure.md                This file
│   └── workings_soft_shell_calculator.md   Background on the soft shell calculation method
├── logs/                                   Runtime log files (not committed)
├── tests/                                  Top-level test directory (not inside src/)
└── src/
    └── soft_shell_calculator_lib/
        ├── __init__.py                     Public API exports
        ├── py.typed                        PEP 561 marker (library ships type hints)
        ├── constants.py                    All algorithm constants and magic numbers
        ├── utils.py                        Shared utilities: logger setup, name comparison
        ├── calculator.py                   Signal processing and calculation logic
        └── models/
            ├── __init__.py                 Re-exports all public model classes
            ├── rpd_measurement.py          RPDMeasurement — one .rgp file
            ├── wooden_pile.py              WoodenPile — one physical pile with its measurements
            ├── construction_part.py        ConstructionPart — a group of piles
            └── retaining_wall.py          RetainingWall — the top-level domain object
```

---

## Module responsibilities

### `models/rpd_measurement.py`
Represents a single RPD measurement loaded from one `.rgp` file. Holds the raw data from the file: the drill signal array, resolution, measurement date, and identifiers. Contains the `from_rgp_file` classmethod that parses the JSON and constructs the object.

**What belongs here:** data fields, file parsing, field validation.  
**What does not belong here:** any signal processing or calculations.

### `models/wooden_pile.py`
Represents a physical wooden pile. A pile has one or two `RPDMeasurement` objects (one drill pass per side). Exposes derived properties such as `diameter`, `number_of_annual_rings`, `sapwood_thickness`, and `soft_shell_thickness`. These properties delegate their computation to the calculator module.

**What belongs here:** domain properties, relationships to measurements.  
**What does not belong here:** the calculation logic itself (that lives in `calculator.py`).

### `models/construction_part.py`
Groups a set of `WoodenPile` objects that belong to the same structural element (e.g. a single foundation section).

### `models/retaining_wall.py`
The top-level domain object. Represents a full retaining wall composed of `ConstructionPart` objects.

### `calculator.py`
Contains all signal processing and numerical calculation logic extracted from the TU Delft script. This is pure computation: functions take data arrays and parameters as input and return results. No UI, no file I/O, no side effects.

See the module docstring in `calculator.py` for the full list of functions it will contain.

### `constants.py`
All numerical constants used by the algorithm. No magic numbers anywhere else in the codebase; every tunable value is defined once here with a descriptive name and a comment explaining its origin.

### `utils.py`
Shared utility functions:
- Logger setup (`get_logger`) — configures structured logging to `logs/` for the library
- Name comparison (`pair_similar_names`) — matches pairs of measurement filenames from the same pole based on string similarity

### `__init__.py`
Exposes the public API of the library. Consumers should be able to import everything they need from `soft_shell_calculator_lib` directly without knowing the internal module layout.

---

## Domain hierarchy

The domain model mirrors the physical structure of a foundation inspection:

```
RetainingWall
└── ConstructionPart (one or more)
    └── WoodenPile (one or more)
        └── RPDMeasurement (one or two — one per drill direction)
```

A `WoodenPile` normally has two `RPDMeasurement` objects: one drill pass entering from each side. The paired measurements are averaged to produce a single estimate for the pile.

---

## Units

All spatial values throughout the library use **millimetres (mm)**. This matches the resolution unit in the `.rgp` file format (`resolutionFeed` in samples/mm) and the TU Delft script.
