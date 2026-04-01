"""Tests for RPDMeasurement.from_rgp_file."""

from pathlib import Path

import pytest

from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement


class TestFromRgpFile:
    def test_loads_valid_file(self, sample_rgp_path: Path) -> None:
        """Should load without error and return an RPDMeasurement."""
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert isinstance(measurement, RPDMeasurement)

    def test_id_equals_filename_stem(self, sample_rgp_path: Path) -> None:
        """The id should be the filename without the extension."""
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert measurement.id == sample_rgp_path.stem

    def test_id_number_is_string(self, sample_rgp_path: Path) -> None:
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert isinstance(measurement.id_number, str)
        assert len(measurement.id_number) > 0

    def test_date_is_populated(self, sample_rgp_path: Path) -> None:
        """Date should be a valid datetime with non-zero year."""
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert measurement.date.year > 2000

    def test_resolution_is_positive_int(self, sample_rgp_path: Path) -> None:
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert isinstance(measurement.resolution, int)
        assert measurement.resolution > 0

    def test_drill_signal_is_non_empty_list(self, sample_rgp_path: Path) -> None:
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert isinstance(measurement.drill_signal, list)
        assert len(measurement.drill_signal) > 0

    def test_drill_signal_contains_floats(self, sample_rgp_path: Path) -> None:
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert all(isinstance(v, (int, float)) for v in measurement.drill_signal[:10])

    def test_raises_on_wrong_extension(self, tmp_path: Path) -> None:
        """A file with a non-.rgp extension should raise ValueError."""
        wrong = tmp_path / "measurement.txt"
        wrong.write_text("{}")
        with pytest.raises(ValueError, match=".rgp"):
            RPDMeasurement.from_rgp_file(wrong)

    def test_raises_on_nonexistent_file(self, tmp_path: Path) -> None:
        """A missing file should raise FileNotFoundError."""
        missing = tmp_path / "missing.rgp"
        with pytest.raises(FileNotFoundError):
            RPDMeasurement.from_rgp_file(missing)

    def test_raises_on_missing_header_field(self, tmp_path: Path) -> None:
        """An .rgp file missing required header fields should raise KeyError."""
        import json

        incomplete = tmp_path / "incomplete.rgp"
        incomplete.write_text(json.dumps({"header": {}, "profile": {"drill": [1.0]}}))
        with pytest.raises(KeyError):
            RPDMeasurement.from_rgp_file(incomplete)

    def test_all_sample_files_load(self, all_rgp_paths: list[Path]) -> None:
        """Every .rgp file in the test dataset should load without error."""
        for path in all_rgp_paths:
            measurement = RPDMeasurement.from_rgp_file(path)
            assert measurement.id == path.stem
