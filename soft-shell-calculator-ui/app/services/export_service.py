"""Export generation service for the VIKTOR app.

This module should assemble downloadable artifacts such as CSV summaries and
zip archives containing generated figures, keeping file generation out of the
controller layer.
"""


def get_supported_export_formats() -> tuple[str, ...]:
    """Return the export formats planned for the app.

    Returns:
        Tuple of placeholder export format names.
    """
    return ("csv", "zip")
