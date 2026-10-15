"""Tests for utility functions in the utils module."""

from pathlib import Path

import pytest

from soft_shell_calculator_lib.utils import (
    MeasurementIdentifier,
    natural_sort_key,
    pair_measurements,
)


class TestMeasurementIdentifierFromFilenameStem:
    def test_parses_standard_filename(self) -> None:
        m = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.100_BM059")
        assert m.retaining_wall_id == "DYG0101"
        assert m.construction_part_id == "CON.A"
        assert m.pile_id == "P1.100"
        assert m.measurement_id == "BM059"

    def test_measurement_id_with_underscores_in_last_part(self) -> None:
        """maxsplit=3 ensures extra underscores in the last segment are preserved."""
        m = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077_extra")
        assert m.measurement_id == "BM077_extra"

    def test_raises_on_too_few_parts(self) -> None:
        with pytest.raises(ValueError, match="expected format"):
            MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1")

    def test_raises_on_empty_string(self) -> None:
        with pytest.raises(ValueError):
            MeasurementIdentifier.from_filename_stem("")


class TestMeasurementIdentifierFromIdNumber:
    def test_parses_standard_id_number(self) -> None:
        m = MeasurementIdentifier.from_id_number("DYG0101/CON.A/P1.100/B", 59)
        assert m.retaining_wall_id == "DYG0101"
        assert m.construction_part_id == "CON.A"
        assert m.pile_id == "P1.100"
        assert m.measurement_id == "59"

    def test_parses_id_number_without_measurement_part(self) -> None:
        m = MeasurementIdentifier.from_id_number("DYG0101/CON.A/P1.100", "7")
        assert m.pile_id == "P1.100"
        assert m.measurement_id == "7"

    def test_raises_on_wrong_separator(self) -> None:
        with pytest.raises(ValueError, match="expected format"):
            MeasurementIdentifier.from_id_number("DYG0101_CON.A_P1.100_B", 1)

    def test_raises_on_too_few_parts(self) -> None:
        with pytest.raises(ValueError):
            MeasurementIdentifier.from_id_number("DYG0101/CON.A", 1)

    def test_raises_on_too_many_parts(self) -> None:
        with pytest.raises(ValueError):
            MeasurementIdentifier.from_id_number("A/B/C/D/E", 1)


class TestMeasurementIdentifierFromRgpFile:
    def test_prefers_header(self) -> None:
        m = MeasurementIdentifier.from_rgp_file(
            Path("DYG0101_CON.A_P1.100_BM059.rgp"), "DYG0101/CON.A/P1.100/B", 59
        )
        assert m.measurement_id == "59"

    def test_header_wins_over_conflicting_filename(self) -> None:
        m = MeasurementIdentifier.from_rgp_file(
            Path("OTHER_CON.B_P9.9_BM001.rgp"), "DYG0101/CON.A/P1.100/B", 59
        )
        assert m.pile_key == ("DYG0101", "CON.A", "P1.100")

    def test_falls_back_to_filename_without_header_values(self) -> None:
        m = MeasurementIdentifier.from_rgp_file(
            Path("DYG0101_CON.A_P1.100_BM059.rgp")
        )
        assert m.measurement_id == "BM059"

    def test_falls_back_to_filename_on_malformed_id_number(self) -> None:
        m = MeasurementIdentifier.from_rgp_file(
            Path("DYG0101_CON.A_P1.100_BM059.rgp"), "bad", 59
        )
        assert m.measurement_id == "BM059"

    def test_raises_when_both_sources_invalid(self) -> None:
        with pytest.raises(ValueError, match="expected format"):
            MeasurementIdentifier.from_rgp_file(Path("badname.rgp"), "bad", 1)

    def test_raises_when_filename_invalid_and_no_header_values(self) -> None:
        with pytest.raises(ValueError, match="expected format"):
            MeasurementIdentifier.from_rgp_file(Path("badname.rgp"))


class TestMeasurementIdentifierPileKey:
    def test_pile_key_ignores_measurement_id(self) -> None:
        m1 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        m2 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM078")
        assert m1.pile_key == m2.pile_key

    def test_pile_key_differs_for_different_piles(self) -> None:
        m1 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        m2 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.2_BM080")
        assert m1.pile_key != m2.pile_key

    def test_pile_key_is_three_tuple(self) -> None:
        m = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        assert isinstance(m.pile_key, tuple)
        assert len(m.pile_key) == 3


class TestMeasurementIdentifierEquality:
    def test_same_values_are_equal(self) -> None:
        m1 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        m2 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        assert m1 == m2

    def test_different_measurement_ids_are_not_equal(self) -> None:
        m1 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        m2 = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM078")
        assert m1 != m2

    def test_is_hashable(self) -> None:
        """frozen=True means MeasurementIdentifier can be used as a dict key."""
        m = MeasurementIdentifier.from_filename_stem("DYG0101_CON.A_P1.1_BM077")
        mapping = {m: "value"}
        assert mapping[m] == "value"


class TestPairMeasurements:
    def test_pairs_two_measurements_of_same_pile(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.A_P1.1_BM078",
        ]
        pairs = pair_measurements(names)
        assert len(pairs) == 1
        assert set(pairs[0]) == set(names)

    def test_does_not_pair_different_piles(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.A_P1.2_BM080",
        ]
        pairs = pair_measurements(names)
        assert len(pairs) == 0

    def test_does_not_pair_different_construction_parts(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.B_P1.1_BM078",
        ]
        pairs = pair_measurements(names)
        assert len(pairs) == 0

    def test_does_not_pair_different_retaining_walls(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "NHG0302_CON.A_P1.1_BM078",
        ]
        pairs = pair_measurements(names)
        assert len(pairs) == 0

    def test_multiple_pairs_from_multiple_piles(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.A_P1.1_BM078",
            "DYG0101_CON.A_P1.2_BM080",
            "DYG0101_CON.A_P1.2_BM081",
        ]
        pairs = pair_measurements(names)
        assert len(pairs) == 2

    def test_unpaired_single_measurement_is_excluded(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",  # has a pair
            "DYG0101_CON.A_P1.1_BM078",
            "DYG0101_CON.A_P1.9_BM099",  # no pair
        ]
        pairs = pair_measurements(names)
        assert len(pairs) == 1
        paired_names = {name for pair in pairs for name in pair}
        assert "DYG0101_CON.A_P1.9_BM099" not in paired_names

    def test_empty_input_returns_empty(self) -> None:
        assert pair_measurements([]) == []

    def test_single_name_returns_empty(self) -> None:
        assert pair_measurements(["DYG0101_CON.A_P1.1_BM077"]) == []

    def test_unparseable_name_is_skipped_with_warning(self, caplog) -> None:
        import logging

        names = ["not-a-valid-name", "DYG0101_CON.A_P1.1_BM077"]
        with caplog.at_level(logging.WARNING, logger="soft_shell_calculator_lib"):
            pairs = pair_measurements(names)
        assert len(pairs) == 0
        assert any("not-a-valid-name" in record.message for record in caplog.records)

    def test_returns_list_of_tuples(self) -> None:
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.A_P1.1_BM078",
        ]
        result = pair_measurements(names)
        assert isinstance(result, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in result)


class TestNaturalSortKey:
    def test_numeric_parts_sort_correctly(self) -> None:
        """P1.2 should sort before P1.11."""
        items = ["P1.11", "P1.2", "P1.1"]
        result = sorted(items, key=natural_sort_key)
        assert result == ["P1.1", "P1.2", "P1.11"]

    def test_alphabetic_parts_sort_case_insensitive(self) -> None:
        assert natural_sort_key("CON.A") == natural_sort_key("con.a")

    def test_pure_numeric_string(self) -> None:
        items = ["100", "20", "3"]
        result = sorted(items, key=natural_sort_key)
        assert result == ["3", "20", "100"]

    def test_mixed_prefix(self) -> None:
        items = ["BM100", "BM9", "BM22"]
        result = sorted(items, key=natural_sort_key)
        assert result == ["BM9", "BM22", "BM100"]

    def test_empty_string(self) -> None:
        assert natural_sort_key("") == ("",)
