"""Plot generation service for the VIKTOR app."""

import statistics

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ui_app.view_models import PileRow, WallAnalysisResult

_COLOUR_SOFT_SHELL = "#F08080"  # light coral
_COLOUR_SAPWOOD = "#90EE90"  # light green
_COLOUR_HEARTWOOD = "#228B22"  # forest green
_COLOUR_BAR = "#4682B4"  # steel blue – raw signal
_COLOUR_PROCESSED = "#1A73E8"  # blue – trimmed signal
_COLOUR_MOVAV = "#D62728"  # red – moving average
_COLOUR_GREY = "#AAAAAA"  # second measurement
_POLAR_R_LIM = 200


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_diameter_histogram(wall_result: WallAnalysisResult) -> go.Figure:
    """Build a bar chart of pile diameters sorted by ascending diameter.

    Args:
        wall_result: Analysis result for one retaining wall.

    Returns:
        A Plotly figure with one bar per pile, sorted by diameter.
    """
    rows_with_diameter = [r for r in wall_result.pile_rows if r.diameter_mm is not None]
    sorted_rows = sorted(rows_with_diameter, key=lambda r: r.diameter_mm)  # type: ignore[arg-type]

    pile_ids = [r.pile_id for r in sorted_rows]
    diameters = [r.diameter_mm for r in sorted_rows]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=pile_ids,
            y=diameters,
            marker_color=_COLOUR_BAR,
            name="Diameter",
        )
    )

    if diameters:
        median_diameter = statistics.median(diameters)  # type: ignore[arg-type]
        fig.add_hline(
            y=median_diameter,
            line_dash="dash",
            line_color=_COLOUR_MOVAV,
            annotation_text=f"Mediaan: {median_diameter:.1f} mm",
            annotation_position="top right",
        )

    fig.update_layout(
        title=f"Paaldiameters — {wall_result.summary.retaining_wall_id}",
        yaxis_title="Diameter [mm]",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin={"l": 60, "r": 20, "t": 50, "b": 60},
    )
    return fig


def build_polar_cross_section(pile_row: PileRow) -> go.Figure:
    """Build a polar bar chart showing asymmetric cross-section zones for one pile.

    Args:
        pile_row: Pile-level analysis result containing thickness data.

    Returns:
        A Plotly figure with polar bar traces or a 'Geen data beschikbaar' annotation.
    """
    fig = go.Figure()
    required = (
        pile_row.soft_shell_entrance_mm,
        pile_row.soft_shell_exit_mm,
        pile_row.sapwood_thickness_mm,
        pile_row.heartwood_thickness_mm,
        pile_row.diameter_mm,
    )
    if any(v is None for v in required):
        fig.add_annotation(
            text="Geen data beschikbaar",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 16},
        )
        fig.update_layout(title=f"Dwarsdoorsnede — {pile_row.pile_id}")
        return fig

    _add_polar_traces(fig, pile_row, polar_ref="polar", show_legend=True)
    fig.update_layout(
        title=f"Dwarsdoorsnede — {pile_row.pile_id}",
        polar={
            "radialaxis": {"range": [0, _POLAR_R_LIM], "visible": False},
            "angularaxis": {"visible": False},
        },
        showlegend=True,
    )
    return fig


def build_pile_figure(pile_row: PileRow) -> go.Figure:
    """Build a two-subplot figure: resistance (left) + cross-section (right).

    Args:
        pile_row: Pile-level analysis result.

    Returns:
        A Plotly figure with drilling resistance and polar cross-section side by side.
    """
    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "xy"}, {"type": "polar"}]],
        subplot_titles=[
            f"Boorweerstand — {pile_row.pile_id}",
            f"Dwarsdoorsnede — {pile_row.pile_id}",
        ],
        column_widths=[0.6, 0.4],
    )

    _add_resistance_traces(fig, pile_row, row=1, col=1)
    _add_polar_traces(fig, pile_row, polar_ref="polar", show_legend=True)

    fig.update_layout(
        height=500,
        title_text=f"Paal {pile_row.pile_id}",
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
        legend={"x": 1.12, "y": 0.5, "xanchor": "left", "tracegroupgap": 16},
        polar={
            "radialaxis": {"range": [0, _POLAR_R_LIM], "visible": False},
            "angularaxis": {"visible": False},
        },
    )
    return fig


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _add_resistance_traces(
    fig: go.Figure, pile_row: PileRow, row: int, col: int
) -> None:
    """Add drilling resistance traces and zone spans for one pile.

    Args:
        fig: Figure to add traces to.
        pile_row: Pile data containing signals and geometry.
        row: Subplot row index (1-based).
        col: Subplot column index (1-based).
    """
    resolution = pile_row.resolutions[0] if pile_row.resolutions else 1

    # Trimmed/filtered signal (blue) — aligned at trim offset
    if pile_row.processed_signals and pile_row.processed_signals[0]:
        offset = pile_row.trim_offsets[0] if pile_row.trim_offsets else 0.0
        proc = pile_row.processed_signals[0]
        proc_depth = [offset + i / resolution for i in range(len(proc))]
        fig.add_trace(
            go.Scatter(
                x=proc_depth,
                y=list(proc),
                mode="lines",
                name="Gefilterd signaal",
                line={"color": _COLOUR_PROCESSED, "width": 1},
                showlegend=True,
                legendgroup="signals",
                legendgrouptitle_text="Boorweerstand",
            ),
            row=row,
            col=col,
        )

        # Moving average (red)
        if pile_row.moving_averages and pile_row.moving_averages[0]:
            movav = pile_row.moving_averages[0]
            fig.add_trace(
                go.Scatter(
                    x=proc_depth[: len(movav)],
                    y=list(movav),
                    mode="lines",
                    name="Voortschrijdend gemiddelde",
                    line={"color": _COLOUR_MOVAV, "width": 2},
                    showlegend=True,
                    legendgroup="signals",
                ),
                row=row,
                col=col,
            )

    # Zone spans and KPI lines (only if we have geometry)
    diameter = pile_row.diameter_mm
    soft_entrance = pile_row.soft_shell_entrance_mm
    soft_exit = pile_row.soft_shell_exit_mm
    sapwood = pile_row.sapwood_thickness_mm

    if (
        diameter is None
        or not pile_row.processed_signals
        or not pile_row.processed_signals[0]
    ):
        fig.update_xaxes(title_text="Diepte [mm]", row=row, col=col)
        fig.update_yaxes(title_text="Weerstand [%]", row=row, col=col)
        return

    offset = pile_row.trim_offsets[0] if pile_row.trim_offsets else 0.0
    suffix = "" if row == 1 else str(row)
    xref = f"x{suffix}"
    yref = f"y{suffix}"

    # Coloured background spans — clipped so soft shell never overlaps heartwood/sapwood
    centre = offset + diameter / 2
    heartwood = pile_row.heartwood_thickness_mm
    pile_end = offset + diameter

    # Boundaries of the sound-wood zone (everything inside the soft shells)
    sound_start = offset + (soft_entrance or 0.0)
    sound_end = pile_end - (soft_exit or 0.0)

    if heartwood:
        hw_x0 = max(centre - heartwood, sound_start)
        hw_x1 = min(centre + heartwood, sound_end)
        if hw_x0 < hw_x1:
            fig.add_vrect(
                x0=hw_x0,
                x1=hw_x1,
                fillcolor=_COLOUR_HEARTWOOD,
                opacity=0.15,
                layer="below",
                line_width=0,
                row=row,
                col=col,
            )
    # Sapwood zone — left side and right side, each clipped to sound wood region
    if sapwood and heartwood:
        # Left sapwood: between sound_start and heartwood left edge
        sp_left_x0 = max(centre - heartwood - sapwood, sound_start)
        sp_left_x1 = min(centre - heartwood, sound_end)
        if sp_left_x0 < sp_left_x1:
            fig.add_vrect(
                x0=sp_left_x0,
                x1=sp_left_x1,
                fillcolor=_COLOUR_SAPWOOD,
                opacity=0.2,
                layer="below",
                line_width=0,
                row=row,
                col=col,
            )
        # Right sapwood: between heartwood right edge and sound_end
        sp_right_x0 = max(centre + heartwood, sound_start)
        sp_right_x1 = min(centre + heartwood + sapwood, sound_end)
        if sp_right_x0 < sp_right_x1:
            fig.add_vrect(
                x0=sp_right_x0,
                x1=sp_right_x1,
                fillcolor=_COLOUR_SAPWOOD,
                opacity=0.2,
                layer="below",
                line_width=0,
                row=row,
                col=col,
            )
    # Soft shell zones (entrance and exit sides)
    if soft_entrance:
        fig.add_vrect(
            x0=offset,
            x1=offset + soft_entrance,
            fillcolor=_COLOUR_SOFT_SHELL,
            opacity=0.25,
            layer="below",
            line_width=0,
            row=row,
            col=col,
        )
    if soft_exit:
        fig.add_vrect(
            x0=pile_end - soft_exit,
            x1=pile_end,
            fillcolor=_COLOUR_SOFT_SHELL,
            opacity=0.25,
            layer="below",
            line_width=0,
            row=row,
            col=col,
        )

    # Vertical dashed KPI lines — boundaries consistent with vrect geometry
    _KPI_SOFT = "#E05050"  # coral-red for soft shell boundaries
    _KPI_SPINT = "#D07000"  # orange for sapwood boundaries
    _KPI_CENTRE = "#888888"  # grey for centre

    kpi_shapes: list[tuple[float, str, str]] = [
        (centre, _KPI_CENTRE, "dot"),  # centre of pile
    ]
    if soft_entrance:
        kpi_shapes.append((offset + soft_entrance, _KPI_SOFT, "dash"))
    if soft_exit:
        kpi_shapes.append((offset + diameter - soft_exit, _KPI_SOFT, "dash"))
    if heartwood is not None and sapwood is not None:
        kpi_shapes.append((centre - heartwood - sapwood, _KPI_SPINT, "dash"))
        kpi_shapes.append((centre + heartwood + sapwood, _KPI_SPINT, "dash"))

    for x_val, colour, dash in kpi_shapes:
        fig.add_shape(
            type="line",
            x0=x_val,
            x1=x_val,
            y0=0,
            y1=1,
            xref=xref,
            yref=f"{yref} domain",
            line={"dash": dash, "color": colour, "width": 1.5},
        )

    # Invisible dummy traces so KPI lines appear in the legend
    _legend_lines: list[tuple[str, str, str, bool]] = [
        ("Middelpunt", _KPI_CENTRE, "dot", False),
        ("Zachte schil", _KPI_SOFT, "dash", bool(soft_entrance or soft_exit)),
        (
            "Spinthout",
            _KPI_SPINT,
            "dash",
            heartwood is not None and sapwood is not None,
        ),
    ]
    first = True
    for name, colour, dash, enabled in _legend_lines:
        if not enabled:
            continue
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                name=name,
                line={"color": colour, "dash": dash, "width": 1.5},
                showlegend=True,
                legendgroup="lines",
                legendgrouptitle_text="KPI-lijnen" if first else None,
            ),
            row=row,
            col=col,
        )
        first = False

    fig.update_xaxes(title_text="Diepte [mm]", row=row, col=col)
    fig.update_yaxes(title_text="Weerstand [%]", row=row, col=col)


def _add_polar_traces(
    fig: go.Figure,
    pile_row: PileRow,
    polar_ref: str,
    show_legend: bool,
) -> None:
    """Add asymmetric polar bar traces for one pile's cross-section zones.

    Order from outside in: soft shell → sapwood → heartwood.
    Left half (entrance) and right half (exit) have independent soft shell widths.

    Args:
        fig: Figure to add traces to.
        pile_row: Pile data containing thickness measurements.
        polar_ref: Name of the polar subplot axis (e.g. 'polar', 'polar2').
        show_legend: Whether to show legend items for these traces.
    """
    required = (
        pile_row.soft_shell_entrance_mm,
        pile_row.soft_shell_exit_mm,
        pile_row.sapwood_thickness_mm,
        pile_row.heartwood_thickness_mm,
        pile_row.diameter_mm,
    )
    if any(v is None for v in required):
        return

    R = pile_row.diameter_mm / 2  # type: ignore[operator]
    heartwood = pile_row.heartwood_thickness_mm  # type: ignore[arg-type]
    sapwood = pile_row.sapwood_thickness_mm  # type: ignore[arg-type]
    soft_entrance = pile_row.soft_shell_entrance_mm  # type: ignore[arg-type]
    soft_exit = pile_row.soft_shell_exit_mm  # type: ignore[arg-type]

    # Heartwood — innermost, full circle
    fig.add_trace(
        go.Barpolar(
            r=[heartwood],
            base=[0],
            theta=[0],
            width=[360],
            marker_color=_COLOUR_HEARTWOOD,
            name=f"Kernhout ({heartwood:.0f} mm)",
            showlegend=show_legend,
            legendgroup="polar",
            legendgrouptitle_text="Dwarsdoorsnede",
            subplot=polar_ref,
        )
    )

    # Sapwood (spinthout) — ring between heartwood and soft shell
    fig.add_trace(
        go.Barpolar(
            r=[sapwood],
            base=[heartwood],
            theta=[0],
            width=[360],
            marker_color=_COLOUR_SAPWOOD,
            name=f"Spinthout ({sapwood:.0f} mm)",
            showlegend=show_legend,
            legendgroup="polar",
            subplot=polar_ref,
        )
    )

    # Soft shell — outermost, asymmetric: links=180° (9 o'clock), rechts=0° (3 o'clock)
    fig.add_trace(
        go.Barpolar(
            r=[soft_entrance],
            base=[R - soft_entrance],
            theta=[180],
            width=[180],
            marker_color=_COLOUR_SOFT_SHELL,
            name=f"Zachte schil links ({soft_entrance:.0f} mm)",
            showlegend=show_legend,
            legendgroup="polar",
            subplot=polar_ref,
        )
    )
    fig.add_trace(
        go.Barpolar(
            r=[soft_exit],
            base=[R - soft_exit],
            theta=[0],
            width=[180],
            marker_color=_COLOUR_SOFT_SHELL,
            name=f"Zachte schil rechts ({soft_exit:.0f} mm)",
            showlegend=show_legend,
            legendgroup="polar",
            subplot=polar_ref,
        )
    )

    # Zone thickness labels inside each zone
    for r_val, theta_val, text, colour in [
        (heartwood / 2, 90, f"{heartwood:.0f}mm", "white"),
        (heartwood + sapwood / 2, 90, f"{sapwood:.0f}mm", "#1a5216"),
        (R - soft_entrance / 2, 180, f"{soft_entrance:.0f}mm", "#8b1a1a"),
        (R - soft_exit / 2, 0, f"{soft_exit:.0f}mm", "#8b1a1a"),
    ]:
        fig.add_trace(
            go.Scatterpolar(
                r=[r_val],
                theta=[theta_val],
                mode="text",
                text=[text],
                textfont={"size": 10, "color": colour},
                showlegend=False,
                subplot=polar_ref,
                hoverinfo="skip",
            )
        )
