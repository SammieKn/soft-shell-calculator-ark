"""Tests for the VIKTOR app service layer.

These tests cover the first app slice: upload ingestion, analysis flattening,
and CSV export.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from ui_app.services.analysis_service import analyze_uploaded_measurements
from ui_app.services.analysis_service import analyze_batch_uploaded_measurements
from ui_app.services.analysis_service import apply_validation_filter
from ui_app.services.analysis_service import get_batch
from ui_app.services.analysis_service import _fingerprint
from ui_app.services.export_service import build_pile_csv
from ui_app.services.export_service import build_batch_csv_zip
from ui_app.services.upload_service import load_uploaded_measurements
from ui_app.services.upload_service import peek_wall_id_from_file_resource
from ui_app.view_models import (
    BatchAnalysisResult,
    PileRow,
    WallAnalysisResult,
    WallSummary,
)


class _InMemoryFileHandle:
    """Simple context manager that mimics the VIKTOR file handle API."""

    def __init__(self, content: bytes) -> None:
        self._content = content

    def __enter__(self) -> "_InMemoryFileHandle":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        return None

    def getvalue(self) -> bytes:
        """Return the raw uploaded bytes.

        Returns:
            Raw byte content.
        """
        return self._content


@dataclass
class FakeUploadedFile:
    """Minimal file resource used to test upload handling."""

    filename: str
    content: bytes

    @property
    def file(self) -> _InMemoryFileHandle:
        """Return a file-handle-like object.

        Returns:
            In-memory context manager.
        """
        return _InMemoryFileHandle(self.content)


def _build_zip_upload(file_map: dict[str, bytes]) -> bytes:
    """Build a zip archive in memory.

    Args:
        file_map: Mapping of zip paths to bytes.

    Returns:
        Zip archive bytes.
    """
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in file_map.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _read_file_bytes(path: Path) -> bytes:
    """Read bytes from a path.

    Args:
        path: File path.

    Returns:
        File bytes.
    """
    return path.read_bytes()


class TestUploadService:
    def test_loads_valid_zip_upload(self, all_rgp_paths: list[Path]) -> None:
        """A zip with valid `.rgp` files should produce a retaining wall."""
        zip_content = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:3]}
        )
        uploaded_file = FakeUploadedFile("metingen.zip", zip_content)

        uploaded_measurements = load_uploaded_measurements(uploaded_file)

        assert uploaded_measurements.retaining_wall.id
        assert uploaded_measurements.uploaded_rgp_count == 3
        assert uploaded_measurements.valid_rgp_count == 3
        assert uploaded_measurements.skipped_files == ()

    def test_skips_invalid_rgp_files(self, sample_rgp_path: Path) -> None:
        """Invalid `.rgp` files should be reported as skipped."""
        valid_bytes = _read_file_bytes(sample_rgp_path)
        invalid_bytes = json.dumps({"header": {}}).encode("utf-8")
        zip_content = _build_zip_upload(
            {
                sample_rgp_path.name: valid_bytes,
                "invalid_measurement.rgp": invalid_bytes,
            }
        )
        uploaded_file = FakeUploadedFile("metingen.zip", zip_content)

        uploaded_measurements = load_uploaded_measurements(uploaded_file)

        assert uploaded_measurements.uploaded_rgp_count == 2
        assert uploaded_measurements.valid_rgp_count == 1
        assert uploaded_measurements.skipped_files == ("invalid_measurement.rgp",)


class TestAnalysisService:
    def test_returns_summary_and_pile_rows(self, all_rgp_paths: list[Path]) -> None:
        """Analysis should flatten the uploaded wall into summary and pile rows."""
        zip_content = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:4]}
        )
        uploaded_file = FakeUploadedFile("metingen.zip", zip_content)

        analysis_result = analyze_uploaded_measurements(uploaded_file)

        assert analysis_result.summary.valid_file_count == 4
        assert analysis_result.summary.pile_count == len(analysis_result.pile_rows)
        assert analysis_result.pile_rows


class TestExportService:
    def test_build_pile_csv_contains_headers_and_rows(
        self, all_rgp_paths: list[Path]
    ) -> None:
        """CSV export should contain the header row and pile identifiers."""
        zip_content = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:2]}
        )
        uploaded_file = FakeUploadedFile("metingen.zip", zip_content)
        analysis_result = analyze_uploaded_measurements(uploaded_file)

        csv_content = build_pile_csv(analysis_result).decode("utf-8")

        assert "Retaining wall id" in csv_content
        assert analysis_result.pile_rows[0].pile_id in csv_content


class TestBatchAnalysisService:
    def test_returns_results_for_multiple_zips(self, all_rgp_paths: list[Path]) -> None:
        """Batch analysis should produce one result per valid uploaded zip."""
        zip_a = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:3]}
        )
        zip_b = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[3:6]}
        )
        files = [
            FakeUploadedFile("kade_a.zip", zip_a),
            FakeUploadedFile("kade_b.zip", zip_b),
        ]

        batch = analyze_batch_uploaded_measurements(files)

        assert len(batch.wall_results) == 2
        assert batch.skipped_walls == ()

    def test_skips_invalid_zip_and_continues(self, all_rgp_paths: list[Path]) -> None:
        """A bad zip in the batch should be skipped; valid ones still analyzed."""
        valid_zip = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:3]}
        )
        invalid_bytes = b"this is not a zip"
        files = [
            FakeUploadedFile("geldig.zip", valid_zip),
            FakeUploadedFile("ongeldig.zip", invalid_bytes),
        ]

        batch = analyze_batch_uploaded_measurements(files)

        assert len(batch.wall_results) == 1
        assert "ongeldig.zip" in batch.skipped_walls


class TestGetBatchCaching:
    """Tests for the in-process batch result cache in get_batch."""

    def test_same_files_return_identical_object(
        self, all_rgp_paths: list[Path]
    ) -> None:
        """Calling get_batch twice with the same files returns the exact same object."""
        import ui_app.services.analysis_service as svc

        zip_content = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:3]}
        )
        files = [FakeUploadedFile("kade_cache.zip", zip_content)]
        svc._batch_cache.clear()

        first = get_batch(files)
        second = get_batch(files)

        assert first is second

    def test_fingerprint_is_order_independent(self) -> None:
        """The fingerprint must be the same regardless of file order."""
        file_a = FakeUploadedFile("alpha.zip", b"")
        file_b = FakeUploadedFile("beta.zip", b"")

        assert _fingerprint([file_a, file_b]) == _fingerprint([file_b, file_a])


class TestBatchExportService:
    def test_build_batch_csv_zip_contains_one_csv_per_wall(
        self, all_rgp_paths: list[Path]
    ) -> None:
        """Batch CSV zip should contain one CSV file per successfully analyzed wall."""
        zip_a = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:3]}
        )
        zip_b = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[3:6]}
        )
        files = [
            FakeUploadedFile("kade_a.zip", zip_a),
            FakeUploadedFile("kade_b.zip", zip_b),
        ]
        batch = analyze_batch_uploaded_measurements(files)

        zip_bytes = build_batch_csv_zip(batch)

        with io.BytesIO(zip_bytes) as buf:
            with ZipFile(buf) as archive:
                all_names = archive.namelist()

        csv_names = [n for n in all_names if n.endswith(".csv")]
        assert len(csv_names) == 2
        assert all(name.endswith(".csv") for name in csv_names)


class TestPeekWallId:
    def test_returns_wall_id_from_valid_zip(self, all_rgp_paths: list[Path]) -> None:
        """Peek should return the wall ID without running full analysis."""
        zip_content = _build_zip_upload(
            {path.name: _read_file_bytes(path) for path in all_rgp_paths[:2]}
        )
        uploaded_file = FakeUploadedFile("metingen.zip", zip_content)

        wall_id = peek_wall_id_from_file_resource(uploaded_file)

        assert wall_id is not None
        assert isinstance(wall_id, str)
        assert len(wall_id) > 0

    def test_returns_none_for_invalid_zip(self) -> None:
        """Peek should return None for a file that is not a valid zip."""
        uploaded_file = FakeUploadedFile("corrupt.zip", b"not a zip")

        wall_id = peek_wall_id_from_file_resource(uploaded_file)

        assert wall_id is None


# ---------------------------------------------------------------------------
# Helpers for TestValidationFilter
# ---------------------------------------------------------------------------


def _make_pile_row(
    retaining_wall_id: str, pile_id: str, construction_part_id: str = "D1"
) -> PileRow:
    """Build a minimal PileRow for testing.

    Args:
        retaining_wall_id: Wall identifier.
        pile_id: Pile identifier.
        construction_part_id: Construction part identifier.

    Returns:
        Minimal PileRow instance.
    """
    return PileRow(
        retaining_wall_id=retaining_wall_id,
        construction_part_id=construction_part_id,
        pile_id=pile_id,
        measurement_ids=("M1",),
        measurement_count=1,
        diameter_mm=220.0,
        annual_rings=60,
        sapwood_thickness_mm=50.0,
        heartwood_thickness_mm=60.0,
        soft_shell_entrance_mm=0.0,
        soft_shell_exit_mm=2.0,
        high_drill_amplitude=False,
        asymmetric_soft_shell=False,
        warnings=(),
        status="OK",
        error_message=None,
    )


def _make_wall_summary(wall_id: str, pile_rows: tuple[PileRow, ...]) -> WallSummary:
    """Build a WallSummary consistent with the given pile rows.

    Args:
        wall_id: Retaining wall identifier.
        pile_rows: Pile rows that belong to this wall.

    Returns:
        WallSummary with counts derived from pile_rows.
    """
    return WallSummary(
        source_filename=f"{wall_id}.zip",
        retaining_wall_id=wall_id,
        construction_part_count=1,
        pile_count=len(pile_rows),
        measurement_count=sum(r.measurement_count for r in pile_rows),
        valid_file_count=len(pile_rows),
        skipped_files=(),
        failed_pile_count=0,
        warning_pile_count=0,
    )


class TestValidationFilter:
    """Unit tests for apply_validation_filter."""

    def _make_batch(self) -> tuple[BatchAnalysisResult, list[PileRow]]:
        """Build a two-wall batch with two piles each for filter testing.

        Returns:
            Tuple of (batch, flat list of all pile rows).
        """
        rows_a = (
            _make_pile_row("KadeA", "P1"),
            _make_pile_row("KadeA", "P2"),
        )
        rows_b = (
            _make_pile_row("KadeB", "P3"),
            _make_pile_row("KadeB", "P4"),
        )
        wall_a = WallAnalysisResult(
            summary=_make_wall_summary("KadeA", rows_a), pile_rows=rows_a
        )
        wall_b = WallAnalysisResult(
            summary=_make_wall_summary("KadeB", rows_b), pile_rows=rows_b
        )
        all_rows = list(rows_a) + list(rows_b)
        return (
            BatchAnalysisResult(wall_results=(wall_a, wall_b), skipped_walls=()),
            all_rows,
        )

    def test_empty_exclusion_returns_original_batch(self) -> None:
        """When the exclusion set is empty, the batch is returned unchanged."""
        batch, _ = self._make_batch()

        result = apply_validation_filter(batch, set())

        assert result is batch

    def test_all_included_returns_original_batch(self) -> None:
        """When no piles are excluded, the batch is returned unchanged."""
        batch, _ = self._make_batch()

        result = apply_validation_filter(batch, set())

        assert result is batch

    def test_excluded_pile_is_removed(self) -> None:
        """An excluded pile should not appear in the filtered batch."""
        batch, _ = self._make_batch()

        result = apply_validation_filter(batch, {("KadeA", "P2")})

        all_pile_ids = [
            row.pile_id for wall in result.wall_results for row in wall.pile_rows
        ]
        assert "P2" not in all_pile_ids
        assert "P1" in all_pile_ids

    def test_filtered_summary_counts_are_updated(self) -> None:
        """After filtering, pile_count and measurement_count reflect the remaining piles."""
        batch, _ = self._make_batch()

        result = apply_validation_filter(batch, {("KadeA", "P1")})

        wall_a = next(
            w for w in result.wall_results if w.summary.retaining_wall_id == "KadeA"
        )
        assert wall_a.summary.pile_count == 1
        assert wall_a.summary.measurement_count == 1

    def test_multiple_exclusions_across_walls(self) -> None:
        """Excluding piles from multiple walls should work independently."""
        batch, _ = self._make_batch()

        result = apply_validation_filter(batch, {("KadeA", "P1"), ("KadeB", "P3")})

        remaining = {
            row.pile_id for wall in result.wall_results for row in wall.pile_rows
        }
        assert remaining == {"P2", "P4"}
