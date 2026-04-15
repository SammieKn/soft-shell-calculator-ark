"""Plot generation service for the VIKTOR app.

This module should create Plotly figures for drilling resistance, pile
cross-sections, and construction-part summaries without embedding plot logic
directly in the VIKTOR controller.
"""


def get_plotly_dependency_name() -> str:
    """Return the plotting backend name used by the future implementation.

    Returns:
        Name of the intended plotting library.
    """
    return "plotly"
