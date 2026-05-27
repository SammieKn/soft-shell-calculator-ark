# Soft Shell Calculator – TU Delft

Original soft shell calculator (v1.1) developed by Anindya and revised by Michele Mirra.  
© 2025 TU Delft & Gemeente Amsterdam.

## Disclaimer

> **De TU Delft heeft met een zo groot mogelijke zorgvuldigheid deze tool ontwikkelt maar sluit niet uit dat er fouten in de software zitten.**
> De tool is expliciet bedoeld als experimentele versie voor intern gebruik van de gemeente Amsterdam om ervaring op te doen met de interpretatie van RPD signalen. Dit is geen commerciële versie en de TU Delft beoogt ook niet deze tool als commerciële versie te onderhouden. Zo'n versie kan eventueel in een later stadium met een professionele software-ontwikkelaar verder geprogrammeerd en onderhouden worden.
>
> De soft shell calculator kan alleen een betrouwbare waarde voor de zachte schil afgeven als het signaal van voldoende kwaliteit is. Dit vergt ervaring van de gebruiker om dit te beoordelen.

## Changes from the original

Only marginal changes have been applied to the original source code:

- Dependency management migrated to [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).
- Minor documentation fixes and code formatting.

No calculation logic has been altered.

## Installation

Requires [uv](https://docs.astral.sh/uv/) to be installed.

```bash
cd soft-shell-calculator-tudelft
uv sync
```

## Usage

```bash
uv run python main.py
```

This opens the wxPython GUI. Select the input `.rgp` files via the file dialog and follow the on-screen instructions.
