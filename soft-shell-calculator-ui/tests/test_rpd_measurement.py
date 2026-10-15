"""Tests for RPDMeasurement.from_rgp_file."""

import json
from pathlib import Path

import pytest

from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from soft_shell_calculator_lib.utils import MeasurementIdentifier


class TestFromRgpFile:
    def test_loads_valid_file(self, sample_rgp_path: Path) -> None:
        """Should load without error and return an RPDMeasurement."""
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert isinstance(measurement, RPDMeasurement)

    def test_identifier_is_measurement_identifier(self, sample_rgp_path: Path) -> None:
        """The identifier field should be a MeasurementIdentifier."""
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert isinstance(measurement.identifier, MeasurementIdentifier)

    def test_identifier_parsed_from_header(self, sample_rgp_path: Path) -> None:
        """The identifier should be built from the header idNumber and number."""
        header = json.loads(sample_rgp_path.read_text())["header"]
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        expected = MeasurementIdentifier.from_id_number(
            header["idNumber"], header["number"]
        )
        assert measurement.identifier == expected

    def test_identifier_components_are_non_empty(self, sample_rgp_path: Path) -> None:
        measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
        assert measurement.identifier.retaining_wall_id
        assert measurement.identifier.construction_part_id
        assert measurement.identifier.pile_id
        assert measurement.identifier.measurement_id

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

    def test_raises_on_filename_not_matching_convention(self, tmp_path: Path) -> None:
        """A .rgp file whose name does not follow the naming convention raises ValueError."""
        bad_name = tmp_path / "badname.rgp"
        bad_name.write_text(
            json.dumps(
                {
                    "header": {
                        "dateYear": 2025,
                        "dateMonth": 1,
                        "dateDay": 1,
                        "resolutionFeed": 10,
                    },
                    "profile": {"drill": [1.0]},
                }
            )
        )
        with pytest.raises(ValueError, match="expected format"):
            RPDMeasurement.from_rgp_file(bad_name)

    def test_falls_back_to_filename(self, tmp_path: Path) -> None:
        """Without header idNumber/number the filename stem is used."""
        path = tmp_path / "DYG0101_CON.A_P1.1_BM077.rgp"
        path.write_text(
            json.dumps(
                {
                    "header": {
                        "dateYear": 2025,
                        "dateMonth": 1,
                        "dateDay": 1,
                        "resolutionFeed": 10,
                    },
                    "profile": {"drill": [1.0]},
                }
            )
        )
        measurement = RPDMeasurement.from_rgp_file(path)
        assert measurement.identifier == MeasurementIdentifier(
            "DYG0101", "CON.A", "P1.1", "BM077"
        )

    def test_header_takes_precedence_over_filename(self, tmp_path: Path) -> None:
        """A valid header idNumber and number win over the filename."""
        path = tmp_path / "OTHER_CON.B_P9.9_BM001.rgp"
        path.write_text(
            json.dumps(
                {
                    "header": {
                        "idNumber": "DYG0101/CON.A/P1.1/B",
                        "number": 77,
                        "dateYear": 2025,
                        "dateMonth": 1,
                        "dateDay": 1,
                        "resolutionFeed": 10,
                    },
                    "profile": {"drill": [1.0]},
                }
            )
        )
        measurement = RPDMeasurement.from_rgp_file(path)
        assert measurement.identifier == MeasurementIdentifier(
            "DYG0101", "CON.A", "P1.1", "77"
        )

    def test_raises_on_missing_header_field(self, tmp_path: Path) -> None:
        """An .rgp file missing required header fields should raise KeyError."""
        incomplete = tmp_path / "DYG0101_CON.A_P1.1_BM077.rgp"
        incomplete.write_text(json.dumps({"header": {}, "profile": {"drill": [1.0]}}))
        with pytest.raises(KeyError):
            RPDMeasurement.from_rgp_file(incomplete)

    def test_all_sample_files_load(self, all_rgp_paths: list[Path]) -> None:
        """Every .rgp file in the test dataset should load without error."""
        for path in all_rgp_paths:
            measurement = RPDMeasurement.from_rgp_file(path)
            header = json.loads(path.read_text())["header"]
            assert measurement.identifier == MeasurementIdentifier.from_id_number(
                header["idNumber"], header["number"]
            )
