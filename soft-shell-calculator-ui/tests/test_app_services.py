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
from ui_app.services.export_service import build_pile_csv
from ui_app.services.export_service import build_batch_csv_zip
from ui_app.services.upload_service import load_uploaded_measurements
from ui_app.services.upload_service import peek_wall_id_from_file_resource


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
