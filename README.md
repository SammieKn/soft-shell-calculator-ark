# Soft Shell Calculator

## Description

The Soft Shell Calculator analyzes RPD (Resistograph Pile Drilling) measurements of wooden foundation poles to estimate the structural health of the wood cross-section. It produces estimates for the pile diameter, number of annual growth rings, sapwood width, and soft shell thickness. These outputs are used by Gemeente Amsterdam to assess decay in wooden utility poles without destructive sampling.

## Repository structure

This is a monorepo containing three packages:

```
soft-shell-calculator-ark/
├── data/                           Sample .rgp measurement files for development and testing
├── soft-shell-calculator-lib/      Backend library: data models, file loading, calculations
├── soft-shell-calculator-ui/       Frontend application (Viktor integration)
└── soft-shell-calculator-tudelft/  Original TU Delft script, preserved as reference
```

### `soft-shell-calculator-lib`

The backend library. Framework-agnostic; no UI dependency. Responsible for:
- Loading and parsing `.rgp` measurement files
- Domain models (`RPDMeasurement`, `WoodenPile`, `ConstructionPart`, `RetainingWall`)
- Signal processing and calculations (filtering, ring counting, sapwood and soft shell estimation)

See [`soft-shell-calculator-lib/docs/library_structure.md`](./soft-shell-calculator-lib/docs/library_structure.md) for the full module layout.

### `soft-shell-calculator-ui`

The frontend application built on the Viktor platform. Consumes `soft-shell-calculator-lib` and handles visualizations and user interaction.

### `soft-shell-calculator-tudelft`

The original wxPython desktop application developed by TU Delft (v1.1, Anindya and Michele Mirra). Preserved unchanged as the reference implementation. The algorithms and domain knowledge in this script form the basis for the refactored library.

See [`soft-shell-calculator-tudelft/docs/current_workings_script.md`](./soft-shell-calculator-tudelft/docs/current_workings_script.md) for a detailed explanation of how the original script works.

## Source recognition

This application is built on the original code and algorithms developed by TU Delft in collaboration with Gemeente Amsterdam.
The original implementation can be found in [`soft-shell-calculator-tudelft/`](./soft-shell-calculator-tudelft/).