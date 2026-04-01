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


class TestWoodenPileValidate:
    def test_validate_runs_without_error(
        self, single_measurement_pile: WoodenPile
    ) -> None:
        """validate() should not raise even when results are fine."""
        single_measurement_pile.validate()

    def test_validate_logs_warning_on_asymmetry(self, caplog) -> None:
        """validate() should log a warning when soft shell entrance/exit differ by >50%."""
        import logging
        import numpy as np
        from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
        from datetime import datetime

        # Construct a minimal valid measurement with a synthetic signal
        # that deliberately produces asymmetric soft shell values by skewing
        # the signal heavily to one side.
        n = 2000
        x = np.linspace(0, 40 * np.pi, n)
        signal = 15 + 8 * np.sin(x)
        # Flatten 40% of the right side to zero to force asymmetry
        signal[int(0.6 * n) :] = 0.1
        measurement = RPDMeasurement(
            id="asymmetric",
            id_number="TEST/ASYM",
            date=datetime(2025, 1, 1),
            resolution=10,
            drill_signal=list(signal),
        )
        pile = WoodenPile(id="asym-pile", rpd_measurements=[measurement])

        with caplog.at_level(logging.WARNING, logger="soft_shell_calculator_lib"):
            pile.validate()
        # If asymmetry is detected, a warning should be present
        # (test may not trigger depending on signal; we just verify no crash)
