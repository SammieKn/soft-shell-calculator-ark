"""UI-facing data structures for the VIKTOR app.

This module should define small dataclasses or typed containers that bridge
domain objects from the calculation library to tables, summaries, plots, and
downloadable exports used by the VIKTOR controller.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryCard:
    """Placeholder summary item for future UI result composition."""

    label: str
    value: str
