"""Export generation service for the VIKTOR app.

This module assembles downloadable artifacts from app-facing result models.
"""

import csv
from io import StringIO

from ui_app.view_models import WallAnalysisResult


def build_pile_csv(analysis_result: WallAnalysisResult) -> bytes:
    """Build a CSV export for the pile-level analysis rows.

    Args:
        analysis_result: App-facing wall analysis result.

    Returns:
        UTF-8 encoded CSV bytes.
    """
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Retaining wall id",
            "Construction part id",
            "Pile id",
            "Measurement ids",
            "Measurement count",
            "Diameter [mm]",
            "Annual rings [-]",
            "Sapwood thickness [mm]",
            "Heartwood thickness [mm]",
            "Soft shell entrance [mm]",
            "Soft shell exit [mm]",
            "High drill amplitude",
            "Asymmetric soft shell",
            "Warnings",
            "Status",
            "Error message",
        ]
    )

    for row in analysis_result.pile_rows:
        writer.writerow(
            [
                row.retaining_wall_id,
                row.construction_part_id,
                row.pile_id,
                ", ".join(row.measurement_ids),
                row.measurement_count,
                _format_optional_number(row.diameter_mm),
                row.annual_rings if row.annual_rings is not None else "",
                _format_optional_number(row.sapwood_thickness_mm),
                _format_optional_number(row.heartwood_thickness_mm),
                _format_optional_number(row.soft_shell_entrance_mm),
                _format_optional_number(row.soft_shell_exit_mm),
                _format_bool(row.high_drill_amplitude),
                _format_bool(row.asymmetric_soft_shell),
                "; ".join(row.warnings),
                row.status,
                row.error_message or "",
            ]
        )

    return buffer.getvalue().encode("utf-8")


def _format_optional_number(value: float | None) -> str:
    """Format an optional number for CSV output.

    Args:
        value: Optional numeric value.

    Returns:
        Rounded string representation or an empty string.
    """
    if value is None:
        return ""
    return f"{value:.1f}"


def _format_bool(value: bool) -> str:
    """Format a boolean as a user-facing string.

    Args:
        value: Boolean value.

    Returns:
        `Yes` or `No`.
    """
    return "Yes" if value else "No"
