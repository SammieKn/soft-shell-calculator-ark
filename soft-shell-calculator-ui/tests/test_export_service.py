"""Tests for the export service: JSON, HTML report, and full batch zip."""

from __future__ import annotations

import io
import json
from zipfile import ZipFile

import pytest

from ui_app.services.export_service import (
    build_batch_zip,
    build_pile_report_html,
    build_wall_json,
)
from ui_app.view_models import (
    BatchAnalysisResult,
    PileRow,
    WallAnalysisResult,
    WallSummary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_pile_row(
    wall_id: str = "DYG0101",
    part_id: str = "CON.A",
    pile_id: str = "P1.1",
    measurement_id: str = "BM001",
    diameter: float = 200.0,
) -> PileRow:
    """Build a minimal PileRow for export testing."""
    return PileRow(
        retaining_wall_id=wall_id,
        construction_part_id=part_id,
        pile_id=pile_id,
        measurement_ids=(measurement_id,),
        measurement_count=1,
        diameter_mm=diameter,
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
        drill_signals=((1.0, 2.0, 3.0),),
        resolutions=(10,),
    )


def _make_wall_result(
    wall_id: str = "DYG0101",
    pile_count: int = 2,
) -> WallAnalysisResult:
    """Build a WallAnalysisResult with the given number of piles."""
    pile_rows = tuple(
        _make_pile_row(wall_id=wall_id, pile_id=f"P1.{i + 1}")
        for i in range(pile_count)
    )
    summary = WallSummary(
        source_filename=f"{wall_id}.zip",
        retaining_wall_id=wall_id,
        construction_part_count=1,
        pile_count=pile_count,
        measurement_count=pile_count,
        valid_file_count=pile_count,
        skipped_files=(),
        failed_pile_count=0,
        warning_pile_count=0,
    )
    return WallAnalysisResult(summary=summary, pile_rows=pile_rows)


def _make_batch(wall_ids: list[str] | None = None) -> BatchAnalysisResult:
    """Build a BatchAnalysisResult with one or more walls."""
    if wall_ids is None:
        wall_ids = ["DYG0101"]
    wall_results = tuple(_make_wall_result(wall_id=wid) for wid in wall_ids)
    return BatchAnalysisResult(wall_results=wall_results, skipped_walls=())


# ---------------------------------------------------------------------------
# Tests: build_wall_json
# ---------------------------------------------------------------------------


class TestBuildWallJson:
    def test_returns_valid_json(self) -> None:
        """Output should be valid UTF-8 JSON."""
        wall_result = _make_wall_result()
        raw = build_wall_json(wall_result)
        payload = json.loads(raw.decode("utf-8"))
        assert isinstance(payload, dict)

    def test_contains_wall_id(self) -> None:
        """JSON should contain the retaining_wall_id at the top level."""
        wall_result = _make_wall_result(wall_id="LEG0402")
        payload = json.loads(build_wall_json(wall_result))
        assert payload["retaining_wall_id"] == "LEG0402"

    def test_contains_source_filename(self) -> None:
        """JSON should contain the source filename."""
        wall_result = _make_wall_result(wall_id="LEG0402")
        payload = json.loads(build_wall_json(wall_result))
        assert payload["source_filename"] == "LEG0402.zip"

    def test_piles_count_matches(self) -> None:
        """Piles list length should match the number of pile rows."""
        wall_result = _make_wall_result(pile_count=3)
        payload = json.loads(build_wall_json(wall_result))
        assert len(payload["piles"]) == 3

    def test_pile_entry_has_expected_keys(self) -> None:
        """Each pile entry should contain the core analysis fields."""
        wall_result = _make_wall_result()
        payload = json.loads(build_wall_json(wall_result))
        pile = payload["piles"][0]
        expected_keys = {
            "retaining_wall_id",
            "construction_part_id",
            "pile_id",
            "measurement_ids",
            "measurement_count",
            "diameter_mm",
            "annual_rings",
            "sapwood_thickness_mm",
            "heartwood_thickness_mm",
            "soft_shell_entrance_mm",
            "soft_shell_exit_mm",
            "high_drill_amplitude",
            "asymmetric_soft_shell",
            "warnings",
            "status",
            "error_message",
        }
        assert expected_keys.issubset(pile.keys())

    def test_numeric_values_are_preserved(self) -> None:
        """Numeric values should round-trip through JSON correctly."""
        wall_result = _make_wall_result()
        payload = json.loads(build_wall_json(wall_result))
        pile = payload["piles"][0]
        assert pile["diameter_mm"] == pytest.approx(200.0)
        assert pile["annual_rings"] == 55

    def test_none_values_serialize_as_null(self) -> None:
        """Piles with failed analysis should serialize None as JSON null."""
        row = PileRow(
            retaining_wall_id="W1",
            construction_part_id="C1",
            pile_id="P1",
            measurement_ids=("M1",),
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
        )
        summary = WallSummary(
            source_filename="W1.zip",
            retaining_wall_id="W1",
            construction_part_count=1,
            pile_count=1,
            measurement_count=1,
            valid_file_count=1,
            skipped_files=(),
            failed_pile_count=1,
            warning_pile_count=0,
        )
        wall_result = WallAnalysisResult(summary=summary, pile_rows=(row,))
        payload = json.loads(build_wall_json(wall_result))
        pile = payload["piles"][0]
        assert pile["diameter_mm"] is None
        assert pile["error_message"] == "Signal too short"


# ---------------------------------------------------------------------------
# Tests: build_pile_report_html
# ---------------------------------------------------------------------------


class TestBuildPileReportHtml:
    def test_returns_valid_html(self) -> None:
        """Output should be UTF-8 HTML with expected structure markers."""
        batch = _make_batch()
        html = build_pile_report_html(batch).decode("utf-8")
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_contains_plotly_cdn_script(self) -> None:
        """HTML should reference the Plotly CDN for rendering charts."""
        batch = _make_batch()
        html = build_pile_report_html(batch).decode("utf-8")
        assert "cdn.plot.ly" in html

    def test_contains_wall_id_in_selector(self) -> None:
        """HTML wall selector should contain the retaining wall ID."""
        batch = _make_batch(wall_ids=["LEG0402"])
        html = build_pile_report_html(batch).decode("utf-8")
        assert "LEG0402" in html

    def test_contains_pile_ids(self) -> None:
        """HTML should contain pile identifiers for navigation."""
        batch = _make_batch()
        html = build_pile_report_html(batch).decode("utf-8")
        assert "P1.1" in html
        assert "P1.2" in html

    def test_multiple_walls_all_present(self) -> None:
        """All walls should appear when batch has multiple walls."""
        batch = _make_batch(wall_ids=["DYG0101", "LEG0402"])
        html = build_pile_report_html(batch).decode("utf-8")
        assert "DYG0101" in html
        assert "LEG0402" in html

    def test_contains_plotly_div(self) -> None:
        """HTML should contain Plotly chart div elements."""
        batch = _make_batch()
        html = build_pile_report_html(batch).decode("utf-8")
        assert "plotly" in html.lower()


# ---------------------------------------------------------------------------
# Tests: build_batch_zip
# ---------------------------------------------------------------------------


class TestBuildBatchZip:
    def test_zip_contains_csv_per_wall(self) -> None:
        """Archive should contain one CSV per wall in data/<wall_id>/ subfolder."""
        batch = _make_batch(wall_ids=["DYG0101", "LEG0402"])
        zip_bytes = build_batch_zip(batch)
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
        assert "data/DYG0101/DYG0101.csv" in names
        assert "data/LEG0402/LEG0402.csv" in names

    def test_zip_contains_json_per_wall(self) -> None:
        """Archive should contain one JSON per wall in data/<wall_id>/ subfolder."""
        batch = _make_batch(wall_ids=["DYG0101", "LEG0402"])
        zip_bytes = build_batch_zip(batch)
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
        assert "data/DYG0101/DYG0101.json" in names
        assert "data/LEG0402/LEG0402.json" in names

    def test_zip_contains_html_report(self) -> None:
        """Archive should contain a single paalrapport.html at the root."""
        batch = _make_batch()
        zip_bytes = build_batch_zip(batch)
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
        assert "paalrapport.html" in names

    def test_csv_content_is_non_empty(self) -> None:
        """CSV files in the archive should contain data (not be empty)."""
        batch = _make_batch()
        zip_bytes = build_batch_zip(batch)
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            csv_bytes = archive.read("data/DYG0101/DYG0101.csv")
        assert len(csv_bytes) > 50  # Header row alone is >50 bytes

    def test_json_content_is_valid(self) -> None:
        """JSON files in the archive should be valid JSON."""
        batch = _make_batch()
        zip_bytes = build_batch_zip(batch)
        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            json_bytes = archive.read("data/DYG0101/DYG0101.json")
        payload = json.loads(json_bytes)
        assert payload["retaining_wall_id"] == "DYG0101"
