"""Tests for the plot generation service."""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from ui_app.services.plot_service import (
    build_diameter_histogram,
    build_pile_figure,
    build_polar_cross_section,
)
from ui_app.view_models import (
    PileRow,
    WallAnalysisResult,
    WallSummary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_pile_row(
    pile_id: str = "P1.1",
    diameter: float | None = 200.0,
    sapwood: float | None = 30.0,
    heartwood: float | None = 70.0,
    soft_entrance: float | None = 5.0,
    soft_exit: float | None = 3.0,
    drill_signal: tuple[float, ...] | None = None,
    resolution: int = 10,
) -> PileRow:
    """Build a PileRow with configurable geometry and signal data."""
    if drill_signal is None:
        # A plausible short signal: 200mm * 10 samples/mm = 2000 samples
        import numpy as np

        rng = np.random.default_rng(42)
        n = 2000
        x = np.linspace(0, 40 * np.pi, n)
        signal = (15 + 8 * np.sin(x) + rng.normal(0, 0.3, n)).clip(min=0.1)
        drill_signal = tuple(float(v) for v in signal)

    return PileRow(
        retaining_wall_id="DYG0101",
        construction_part_id="CON.A",
        pile_id=pile_id,
        measurement_ids=("BM001",),
        measurement_count=1,
        diameter_mm=diameter,
        annual_rings=55,
        sapwood_thickness_mm=sapwood,
        heartwood_thickness_mm=heartwood,
        soft_shell_entrance_mm=soft_entrance,
        soft_shell_exit_mm=soft_exit,
        high_drill_amplitude=False,
        asymmetric_soft_shell=False,
        warnings=(),
        status="OK",
        error_message=None,
        drill_signals=(drill_signal,),
        resolutions=(resolution,),
    )


def _make_pile_row_no_data() -> PileRow:
    """Build a PileRow where all analysis fields are None (failed pile)."""
    return PileRow(
        retaining_wall_id="DYG0101",
        construction_part_id="CON.A",
        pile_id="P1.99",
        measurement_ids=("BM099",),
        measurement_count=1,
        diameter_mm=None,
        annual_rings=None,
        sapwood_thickness_mm=None,
        heartwood_thickness_mm=None,
        soft_shell_entrance_mm=None,
        soft_shell_exit_mm=None,
        high_drill_amplitude=False,
        asymmetric_soft_shell=False,
        warnings=(),
        status="Fout",
        error_message="Signal too short",
        drill_signals=(),
        resolutions=(),
    )


def _make_wall_result(pile_rows: tuple[PileRow, ...]) -> WallAnalysisResult:
    """Build a WallAnalysisResult from the given pile rows."""
    summary = WallSummary(
        source_filename="test.zip",
        retaining_wall_id="DYG0101",
        construction_part_count=1,
        pile_count=len(pile_rows),
        measurement_count=len(pile_rows),
        valid_file_count=len(pile_rows),
        skipped_files=(),
        failed_pile_count=0,
        warning_pile_count=0,
    )
    return WallAnalysisResult(summary=summary, pile_rows=pile_rows)


# ---------------------------------------------------------------------------
# Tests: build_diameter_histogram
# ---------------------------------------------------------------------------


class TestBuildDiameterHistogram:
    def test_returns_figure(self) -> None:
        """Should return a plotly Figure object."""
        rows = tuple(
            _make_pile_row(pile_id=f"P1.{i}", diameter=180.0 + i * 10) for i in range(3)
        )
        wall_result = _make_wall_result(rows)
        fig = build_diameter_histogram(wall_result)
        assert isinstance(fig, go.Figure)

    def test_contains_bar_trace(self) -> None:
        """Figure should contain at least one Bar trace."""
        rows = tuple(
            _make_pile_row(pile_id=f"P1.{i}", diameter=180.0 + i * 10) for i in range(3)
        )
        wall_result = _make_wall_result(rows)
        fig = build_diameter_histogram(wall_result)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1

    def test_bar_trace_has_correct_count(self) -> None:
        """Bar trace should have one bar per pile with a valid diameter."""
        rows = tuple(
            _make_pile_row(pile_id=f"P1.{i}", diameter=180.0 + i * 10) for i in range(4)
        )
        wall_result = _make_wall_result(rows)
        fig = build_diameter_histogram(wall_result)
        bar_trace = next(t for t in fig.data if isinstance(t, go.Bar))
        assert len(bar_trace.y) == 4

    def test_piles_with_none_diameter_excluded(self) -> None:
        """Piles without diameter data should not appear in the histogram."""
        rows = (
            _make_pile_row(pile_id="P1.1", diameter=200.0),
            _make_pile_row(
                pile_id="P1.2",
                diameter=None,
                sapwood=None,
                heartwood=None,
                soft_entrance=None,
                soft_exit=None,
            ),
        )
        wall_result = _make_wall_result(rows)
        fig = build_diameter_histogram(wall_result)
        bar_trace = next(t for t in fig.data if isinstance(t, go.Bar))
        assert len(bar_trace.y) == 1

    def test_has_median_line_when_data_present(self) -> None:
        """Figure should include a median line shape/annotation."""
        rows = tuple(
            _make_pile_row(pile_id=f"P1.{i}", diameter=180.0 + i * 10) for i in range(3)
        )
        wall_result = _make_wall_result(rows)
        fig = build_diameter_histogram(wall_result)
        # Median line is added via add_hline which creates a shape
        fig_json = fig.to_json()
        assert "Mediaan" in fig_json


# ---------------------------------------------------------------------------
# Tests: build_polar_cross_section
# ---------------------------------------------------------------------------


class TestBuildPolarCrossSection:
    def test_returns_figure(self) -> None:
        """Should return a plotly Figure."""
        pile_row = _make_pile_row()
        fig = build_polar_cross_section(pile_row)
        assert isinstance(fig, go.Figure)

    def test_has_polar_traces_when_data_present(self) -> None:
        """Figure should contain Barpolar traces for wood zones."""
        pile_row = _make_pile_row()
        fig = build_polar_cross_section(pile_row)
        polar_traces = [t for t in fig.data if isinstance(t, go.Barpolar)]
        # Expect at least: heartwood, sapwood, soft shell left, soft shell right
        assert len(polar_traces) >= 4

    def test_shows_annotation_when_no_data(self) -> None:
        """Figure should show 'Geen data beschikbaar' when pile has None values."""
        pile_row = _make_pile_row_no_data()
        fig = build_polar_cross_section(pile_row)
        annotations = fig.layout.annotations
        assert len(annotations) >= 1
        assert "Geen data" in annotations[0].text

    def test_no_polar_traces_when_no_data(self) -> None:
        """Figure should have no Barpolar traces when pile data is missing."""
        pile_row = _make_pile_row_no_data()
        fig = build_polar_cross_section(pile_row)
        polar_traces = [t for t in fig.data if isinstance(t, go.Barpolar)]
        assert len(polar_traces) == 0

    def test_title_shows_original_diameter(self) -> None:
        """Figure title should display the original pile diameter."""
        pile_row = _make_pile_row(diameter=200.0, soft_entrance=5.0, soft_exit=3.0)
        fig = build_polar_cross_section(pile_row)
        title_text = fig.layout.title.text or ""
        assert "Diameter paal: 200 mm" in title_text


# ---------------------------------------------------------------------------
# Tests: build_pile_figure
# ---------------------------------------------------------------------------


class TestBuildPileFigure:
    def test_returns_figure(self) -> None:
        """Should return a plotly Figure."""
        pile_row = _make_pile_row()
        fig = build_pile_figure(pile_row)
        assert isinstance(fig, go.Figure)

    def test_has_scatter_traces_for_resistance(self) -> None:
        """Figure should contain Scatter traces for the drilling resistance signal."""
        pile_row = _make_pile_row()
        fig = build_pile_figure(pile_row)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        # At least the filtered signal and moving average
        assert len(scatter_traces) >= 2

    def test_has_polar_traces_for_cross_section(self) -> None:
        """Figure should contain Barpolar traces for the cross-section subplot."""
        pile_row = _make_pile_row()
        fig = build_pile_figure(pile_row)
        polar_traces = [t for t in fig.data if isinstance(t, go.Barpolar)]
        assert len(polar_traces) >= 4

    def test_handles_pile_with_no_signal(self) -> None:
        """Figure should not crash when drill signals are empty."""
        pile_row = _make_pile_row_no_data()
        fig = build_pile_figure(pile_row)
        assert isinstance(fig, go.Figure)

    def test_title_contains_pile_id(self) -> None:
        """Figure title should reference the pile ID."""
        pile_row = _make_pile_row(pile_id="P2.55")
        fig = build_pile_figure(pile_row)
        assert "P2.55" in (fig.layout.title.text or "")

    def test_cross_section_subtitle_shows_original_diameter(self) -> None:
        """Dwarsdoorsnede subtitle should display both original and healthy diameter."""
        pile_row = _make_pile_row(diameter=200.0, soft_entrance=5.0, soft_exit=3.0)
        fig = build_pile_figure(pile_row)
        fig_json = fig.to_json()
        assert "Diameter paal: 200 mm" in fig_json
        assert "Gezonde diameter: 192 mm" in fig_json

    def test_resistance_traces_show_measurement_id_in_hover(self) -> None:
        """Drilling resistance traces should include the measurement ID in hover."""
        pile_row = _make_pile_row()
        fig = build_pile_figure(pile_row)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter) and t.y is not None and len(t.y) > 1]
        # The first signal trace should have measurement ID in hovertemplate
        signal_trace = scatter_traces[0]
        assert "BM001" in (signal_trace.hovertemplate or "")

    def test_multiple_measurements_show_distinct_ids_in_hover(self) -> None:
        """When multiple measurements exist, each trace hover should identify its measurement."""
        import numpy as np

        rng = np.random.default_rng(42)
        n = 2000
        x = np.linspace(0, 40 * np.pi, n)
        signal1 = tuple(float(v) for v in (15 + 8 * np.sin(x) + rng.normal(0, 0.3, n)).clip(min=0.1))
        signal2 = tuple(float(v) for v in (12 + 6 * np.sin(x) + rng.normal(0, 0.3, n)).clip(min=0.1))

        pile_row = PileRow(
            retaining_wall_id="DYG0101",
            construction_part_id="CON.A",
            pile_id="P1.82",
            measurement_ids=("BM001", "BM002"),
            measurement_count=2,
            diameter_mm=200.0,
            annual_rings=55,
            sapwood_thickness_mm=30.0,
            heartwood_thickness_mm=70.0,
            soft_shell_entrance_mm=5.0,
            soft_shell_exit_mm=3.0,
            high_drill_amplitude=False,
            asymmetric_soft_shell=False,
            warnings=(),
            status="OK",
            error_message=None,
            drill_signals=(signal1, signal2),
            resolutions=(10, 10),
        )
        fig = build_pile_figure(pile_row)
        fig_json = fig.to_json()
        assert "BM001" in fig_json
        assert "BM002" in fig_json
