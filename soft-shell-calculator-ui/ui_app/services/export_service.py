"""Export generation service for the VIKTOR app.

This module assembles downloadable artifacts from app-facing result models.
"""

import csv
import json
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from ui_app.view_models import BatchAnalysisResult, WallAnalysisResult


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


def build_wall_json(analysis_result: WallAnalysisResult) -> bytes:
    """Serialise pile results for one wall to JSON bytes.

    Args:
        analysis_result: App-facing wall analysis result.

    Returns:
        UTF-8 encoded JSON bytes.
    """
    piles = [
        {
            "retaining_wall_id": row.retaining_wall_id,
            "construction_part_id": row.construction_part_id,
            "pile_id": row.pile_id,
            "measurement_ids": list(row.measurement_ids),
            "measurement_count": row.measurement_count,
            "diameter_mm": row.diameter_mm,
            "annual_rings": row.annual_rings,
            "sapwood_thickness_mm": row.sapwood_thickness_mm,
            "heartwood_thickness_mm": row.heartwood_thickness_mm,
            "soft_shell_entrance_mm": row.soft_shell_entrance_mm,
            "soft_shell_exit_mm": row.soft_shell_exit_mm,
            "high_drill_amplitude": row.high_drill_amplitude,
            "asymmetric_soft_shell": row.asymmetric_soft_shell,
            "warnings": list(row.warnings),
            "status": row.status,
            "error_message": row.error_message,
        }
        for row in analysis_result.pile_rows
    ]
    payload = {
        "retaining_wall_id": analysis_result.summary.retaining_wall_id,
        "source_filename": analysis_result.summary.source_filename,
        "piles": piles,
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def build_pile_report_html(batch_result: BatchAnalysisResult) -> bytes:
    """Build a single-page HTML report with wall + pile navigation.

    Contains interactive Plotly figures with wall + pile selectors. Plotly.js
    is loaded once from CDN.

    Args:
        batch_result: Batch analysis result with multiple wall results.

    Returns:
        UTF-8 encoded HTML bytes.
    """
    from ui_app.services.plot_service import build_pile_figure

    def safe(text: str) -> str:
        return (
            text.replace(".", "_").replace(" ", "_").replace("/", "_").replace("-", "_")
        )

    # Build data structure: wall_id -> [(safe_pile_id, pile_label, div_html), ...]
    walls: list[tuple[str, str, list[tuple[str, str, str]]]] = []
    first_panel_safe_id: str = ""
    first_safe_wall_id: str = ""

    for wall_result in batch_result.wall_results:
        wall_id = wall_result.summary.retaining_wall_id
        safe_wall_id = safe(wall_id)
        if not first_safe_wall_id:
            first_safe_wall_id = safe_wall_id
        pile_entries: list[tuple[str, str, str]] = []
        for pile_row in wall_result.pile_rows:
            safe_pile_id = f"pile_{safe_wall_id}_{safe(pile_row.pile_id)}"
            fig = build_pile_figure(pile_row)
            div_html = fig.to_html(
                include_plotlyjs=False,
                full_html=False,
                div_id=f"fig_{safe_pile_id}",
                config={"responsive": True},
            )
            pile_entries.append((safe_pile_id, pile_row.pile_id, div_html))
            if not first_panel_safe_id:
                first_panel_safe_id = safe_pile_id
        walls.append((safe_wall_id, wall_id, pile_entries))

    # ---- Graphs tab -------------------------------------------------------
    wall_options_html = "\n      ".join(
        f'<option value="{sw}">{wl}</option>' for sw, wl, _ in walls
    )
    pile_selects_html = "\n".join(
        f'<select id="pile-select-{sw}" class="pile-select"'
        f' style="display:{"block" if i == 0 else "none"}" '
        f'onchange="showPile(this.value)">\n'
        + "\n".join(f'  <option value="{sp}">{pl}</option>' for sp, pl, _ in piles)
        + "\n</select>"
        for i, (sw, _wl, piles) in enumerate(walls)
    )
    panels_html = "\n".join(
        f'<div id="wrap_{sp}" class="pile-panel"'
        f' style="display:{"block" if sp == first_panel_safe_id else "none"}">\n'
        f"  {div_html}\n</div>"
        for _sw, _wl, piles in walls
        for sp, _pl, div_html in piles
    )

    html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <title>Soft Shell Calculator \u2014 Paalrapport</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f5f5f5; font-size: 13px; }}
    h1 {{ color: #2c3e50; margin-bottom: 16px; font-size: 20px; }}
    .nav-bar {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
                margin-bottom: 12px; }}
    .nav-group {{ display: flex; align-items: center; gap: 8px; }}
    .nav-group label {{ font-weight: bold; white-space: nowrap; }}
    select {{ font-size: 13px; padding: 5px 10px; border-radius: 4px;
              border: 1px solid #ccc; min-width: 180px; }}
    .pile-panel {{ min-height: 520px; }}
  </style>
</head>
<body>
  <h1>Soft Shell Calculator \u2014 Paalrapport</h1>

  <div class="nav-bar">
    <div class="nav-group">
      <label for="wall-select">Rak:</label>
      <select id="wall-select" onchange="showWall(this.value)">
        {wall_options_html}
      </select>
    </div>
    <div class="nav-group" id="pile-select-wrapper">
      <label>Paal:</label>
      {pile_selects_html}
    </div>
  </div>
  {panels_html}

  <script>
    function showWall(safeWallId) {{
      document.querySelectorAll('.pile-select').forEach(function(el) {{
        el.style.display = 'none';
      }});
      var sel = document.getElementById('pile-select-' + safeWallId);
      sel.style.display = 'block';
      showPile(sel.value);
    }}
    function showPile(safePileId) {{
      document.querySelectorAll('.pile-panel').forEach(function(el) {{
        el.style.display = 'none';
      }});
      var wrap = document.getElementById('wrap_' + safePileId);
      if (wrap) {{ wrap.style.display = 'block'; }}
      var plotDiv = document.getElementById('fig_' + safePileId);
      if (plotDiv) {{ Plotly.Plots.resize(plotDiv); }}
    }}
  </script>
</body>
</html>"""

    return html.encode("utf-8")


def build_batch_csv_zip(batch_result: BatchAnalysisResult) -> bytes:
    """Build a zip archive containing one CSV file per retaining wall.

    Args:
        batch_result: Batch analysis result with multiple wall results.

    Returns:
        Zip archive bytes with one ``<wall_id>.csv`` entry per wall.
    """
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for wall_result in batch_result.wall_results:
            wall_id = wall_result.summary.retaining_wall_id
            archive.writestr(f"{wall_id}.csv", build_pile_csv(wall_result))
    return buffer.getvalue()


def build_batch_zip(batch_result: BatchAnalysisResult) -> bytes:
    """Build a zip archive with CSV/JSON per wall in subfolders and a single HTML pile report.

    Args:
        batch_result: Batch analysis result with multiple wall results.

    Returns:
        Zip archive with ``data/<wall_id>/<wall_id>.csv``,
        ``data/<wall_id>/<wall_id>.json`` per wall and a single
        ``paalrapport.html`` containing all pile figures.
    """
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for wall_result in batch_result.wall_results:
            wall_id = wall_result.summary.retaining_wall_id
            archive.writestr(
                f"data/{wall_id}/{wall_id}.csv", build_pile_csv(wall_result)
            )
            archive.writestr(
                f"data/{wall_id}/{wall_id}.json", build_wall_json(wall_result)
            )
        archive.writestr("paalrapport.html", build_pile_report_html(batch_result))
    return buffer.getvalue()
