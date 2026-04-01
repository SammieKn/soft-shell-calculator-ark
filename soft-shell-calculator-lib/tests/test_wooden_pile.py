"""Tests for WoodenPile computed properties."""

from pathlib import Path

import pytest

from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from soft_shell_calculator_lib.models.wooden_pile import WoodenPile


@pytest.fixture
def single_measurement_pile(sample_rgp_path: Path) -> WoodenPile:
    """A WoodenPile with one measurement loaded from a real .rgp file."""
    measurement = RPDMeasurement.from_rgp_file(sample_rgp_path)
    return WoodenPile(id="test-pile", rpd_measurements=[measurement])


@pytest.fixture
def two_measurement_pile(all_rgp_paths: list[Path]) -> WoodenPile:
    """A WoodenPile with two measurements from the same directory."""
    if len(all_rgp_paths) < 2:
        pytest.skip("Need at least two .rgp files for pairing test.")
    m1 = RPDMeasurement.from_rgp_file(all_rgp_paths[0])
    m2 = RPDMeasurement.from_rgp_file(all_rgp_paths[1])
    return WoodenPile(id="paired-pile", rpd_measurements=[m1, m2])


class TestWoodenPileProperties:
    def test_diameter_is_positive(self, single_measurement_pile: WoodenPile) -> None:
        assert single_measurement_pile.diameter > 0

    def test_diameter_is_plausible_mm(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        """Typical pile diameter is 100–500 mm."""
        assert 100 < single_measurement_pile.diameter < 500

    def test_number_of_annual_rings_is_positive_int(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        rings = single_measurement_pile.number_of_annual_rings
        assert isinstance(rings, int)
        assert rings > 0

    def test_sapwood_thickness_is_positive(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        assert single_measurement_pile.sapwood_thickness > 0

    def test_heartwood_thickness_is_positive(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        assert single_measurement_pile.heartwood_thickness > 0

    def test_heartwood_equals_radius_minus_sapwood(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        expected = (
            single_measurement_pile.diameter / 2
            - single_measurement_pile.sapwood_thickness
        )
        assert single_measurement_pile.heartwood_thickness == pytest.approx(expected)

    def test_soft_shell_entrance_is_non_negative(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        assert single_measurement_pile.soft_shell_entrance_thickness >= 0

    def test_soft_shell_exit_is_non_negative(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        assert single_measurement_pile.soft_shell_exit_thickness >= 0

    def test_results_are_cached(self, single_measurement_pile: WoodenPile) -> None:
        """Accessing _results twice should return the same object (cached)."""
        first = single_measurement_pile._results
        second = single_measurement_pile._results
        assert first is second

    def test_raises_when_no_measurements(self) -> None:
        pile = WoodenPile(id="empty", rpd_measurements=[])
        with pytest.raises(ValueError, match="no RPD measurements"):
            _ = pile.diameter

    def test_two_measurement_diameter_is_average(
        self, two_measurement_pile: WoodenPile
    ) -> None:
        """Diameter with two measurements should lie between the two individual values."""
        m1, m2 = two_measurement_pile.rpd_measurements
        pile1 = WoodenPile(id="p1", rpd_measurements=[m1])
        pile2 = WoodenPile(id="p2", rpd_measurements=[m2])
        d_avg = (pile1.diameter + pile2.diameter) / 2
        assert two_measurement_pile.diameter == pytest.approx(d_avg)


class TestWoodenPileRemarks:
    def test_has_high_drill_amplitude_false_for_low_signal(self) -> None:
        """A signal well below 75 should not trigger the amplitude remark."""
        from datetime import datetime
        from soft_shell_calculator_lib.utils import MeasurementIdentifier

        low_signal = [10.0] * 500
        m = RPDMeasurement(
            identifier=MeasurementIdentifier("W", "C", "P", "M"),
            date=datetime(2025, 1, 1),
            resolution=10,
            drill_signal=low_signal,
        )
        pile = WoodenPile(id="low-amp", rpd_measurements=[m])
        assert pile.has_high_drill_amplitude is False

    def test_has_high_drill_amplitude_true_for_high_signal(self) -> None:
        """A signal with at least one value above 75 should trigger the amplitude remark."""
        from datetime import datetime
        from soft_shell_calculator_lib.utils import MeasurementIdentifier

        high_signal = [10.0] * 499 + [80.0]
        m = RPDMeasurement(
            identifier=MeasurementIdentifier("W", "C", "P", "M"),
            date=datetime(2025, 1, 1),
            resolution=10,
            drill_signal=high_signal,
        )
        pile = WoodenPile(id="high-amp", rpd_measurements=[m])
        assert pile.has_high_drill_amplitude is True

    def test_has_asymmetric_soft_shell_returns_bool(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        assert isinstance(single_measurement_pile.has_asymmetric_soft_shell, bool)
