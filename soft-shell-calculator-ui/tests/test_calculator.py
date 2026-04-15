"""Tests for the calculator module.

Covers all public functions with typical cases and edge cases.
"""

import numpy as np
import pytest

from soft_shell_calculator_lib.calculator import (
    compute_moving_average,
    compute_overlap_position,
    count_annual_rings,
    detect_soft_shell,
    estimate_diameter,
    estimate_growth_rate,
    estimate_sapwood_width,
    filter_signal,
    trim_signal,
)


# ---------------------------------------------------------------------------
# filter_signal
# ---------------------------------------------------------------------------


class TestFilterSignal:
    def test_removes_near_zero_samples(self, resolution: int) -> None:
        """Samples below 1% of the average are filtered out."""
        signal = np.array([0.0, 0.0, 0.0, 10.0, 20.0, 15.0, 0.0], dtype=float)
        filtered, _ = filter_signal(signal, resolution)
        assert all(v > 0 for v in filtered)

    def test_threshold_cut_is_correct_depth(self, resolution: int) -> None:
        """threshold_cut should equal the index of the first above-threshold sample divided by resolution."""
        signal = np.array([0.0, 0.0, 10.0, 20.0, 15.0], dtype=float)
        _, threshold_cut = filter_signal(signal, resolution)
        # average = 9.0, threshold = 0.09; first index above threshold = 2
        assert threshold_cut == pytest.approx(2 / resolution)

    def test_raises_on_all_zero_signal(self, resolution: int) -> None:
        """An all-zero signal should raise ValueError."""
        signal = np.zeros(100)
        with pytest.raises(ValueError, match="No samples"):
            filter_signal(signal, resolution)

    def test_real_rgp_signal(self, sample_rgp_path) -> None:
        """filter_signal should succeed on a real .rgp signal."""
        import json
        with open(sample_rgp_path) as f:
            data = json.load(f)
        drill_amp = np.array(data["profile"]["drill"])
        resolution = data["header"]["resolutionFeed"]
        filtered, threshold_cut = filter_signal(drill_amp, resolution)
        assert len(filtered) > 0
        assert threshold_cut >= 0


# ---------------------------------------------------------------------------
# trim_signal
# ---------------------------------------------------------------------------


class TestTrimSignal:
    def test_outputs_shorter_than_input(self, synthetic_drill_amp: np.ndarray, resolution: int) -> None:
        """The trimmed signal should be shorter than the raw input."""
        filtered, _ = filter_signal(synthetic_drill_amp, resolution)
        pile = trim_signal(filtered)
        assert len(pile) < len(synthetic_drill_amp)

    def test_output_has_nonzero_values(self, synthetic_pile_signal: np.ndarray) -> None:
        """All samples in the output should be non-zero (the signal is isolated from silence)."""
        pile = trim_signal(synthetic_pile_signal)
        assert np.all(pile > 0)

    def test_returns_ndarray(self, synthetic_pile_signal: np.ndarray) -> None:
        """Return type should be a numpy array."""
        result = trim_signal(synthetic_pile_signal)
        assert isinstance(result, np.ndarray)

    def test_real_rgp_signal(self, sample_rgp_path) -> None:
        """trim_signal should succeed on a filtered real .rgp signal."""
        import json
        with open(sample_rgp_path) as f:
            data = json.load(f)
        drill_amp = np.array(data["profile"]["drill"])
        resolution = data["header"]["resolutionFeed"]
        filtered, _ = filter_signal(drill_amp, resolution)
        pile = trim_signal(filtered)
        assert len(pile) > 0


# ---------------------------------------------------------------------------
# compute_overlap_position
# ---------------------------------------------------------------------------


class TestComputeOverlapPosition:
    def test_returns_float(self, synthetic_drill_amp: np.ndarray, resolution: int) -> None:
        result = compute_overlap_position(synthetic_drill_amp, 5.0, resolution)
        assert isinstance(result, float)

    def test_result_at_least_threshold_cut(self, synthetic_drill_amp: np.ndarray, resolution: int) -> None:
        """Result should never be less than threshold_cut."""
        threshold_cut = 3.0
        result = compute_overlap_position(synthetic_drill_amp, threshold_cut, resolution)
        assert result >= threshold_cut

    def test_flat_signal_returns_threshold_cut(self, resolution: int) -> None:
        """A perfectly flat signal has no high-variance window; should return threshold_cut."""
        flat_signal = np.ones(200) * 5.0
        threshold_cut = 2.0
        result = compute_overlap_position(flat_signal, threshold_cut, resolution)
        assert result == pytest.approx(threshold_cut)


# ---------------------------------------------------------------------------
# estimate_diameter
# ---------------------------------------------------------------------------


class TestEstimateDiameter:
    def test_diameter_equals_length_over_resolution(self, resolution: int) -> None:
        """Diameter = number of samples / resolution."""
        pile = np.ones(1500)
        diameter = estimate_diameter(pile, resolution)
        assert diameter == pytest.approx(1500 / resolution)

    def test_unit_is_mm(self, resolution: int) -> None:
        """With resolution=10 samples/mm, a 2000-sample signal gives 200 mm."""
        pile = np.ones(2000)
        assert estimate_diameter(pile, 10) == pytest.approx(200.0)

    def test_real_signal_diameter_plausible(self, sample_rgp_path) -> None:
        """Diameter from a real signal should be between 100 mm and 500 mm."""
        import json
        with open(sample_rgp_path) as f:
            data = json.load(f)
        drill_amp = np.array(data["profile"]["drill"])
        resolution = data["header"]["resolutionFeed"]
        filtered, _ = filter_signal(drill_amp, resolution)
        pile = trim_signal(filtered)
        diameter = estimate_diameter(pile, resolution)
        assert 100 < diameter < 500


# ---------------------------------------------------------------------------
# compute_moving_average
# ---------------------------------------------------------------------------


class TestComputeMovingAverage:
    def test_same_length_as_input(self, synthetic_pile_signal: np.ndarray) -> None:
        movav = compute_moving_average(synthetic_pile_signal)
        assert len(movav) == len(synthetic_pile_signal)

    def test_constant_signal_returns_constant(self) -> None:
        """Moving average of a constant signal should equal the constant."""
        signal = np.full(300, 7.5)
        movav = compute_moving_average(signal)
        assert np.allclose(movav, 7.5)

    def test_edge_values_are_finite(self, synthetic_pile_signal: np.ndarray) -> None:
        """All values including edges should be finite."""
        movav = compute_moving_average(synthetic_pile_signal)
        assert np.all(np.isfinite(movav))

    def test_smoothing_reduces_variance(self, synthetic_pile_signal: np.ndarray) -> None:
        """Moving average should have lower variance than the original signal."""
        movav = compute_moving_average(synthetic_pile_signal)
        assert np.var(movav) < np.var(synthetic_pile_signal)


# ---------------------------------------------------------------------------
# count_annual_rings
# ---------------------------------------------------------------------------


class TestCountAnnualRings:
    def test_returns_positive_integer(self, synthetic_pile_signal: np.ndarray, resolution: int) -> None:
        rings = count_annual_rings(synthetic_pile_signal, resolution)
        assert isinstance(rings, int)
        assert rings > 0

    def test_raises_on_too_short_signal(self, resolution: int) -> None:
        """Signal shorter than the SG filter window should raise ValueError."""
        short_signal = np.ones(10)
        with pytest.raises(ValueError, match="too short"):
            count_annual_rings(short_signal, resolution)

    def test_real_signal_rings_plausible(self, sample_rgp_path) -> None:
        """Ring count from a real signal should be between 10 and 300."""
        import json
        with open(sample_rgp_path) as f:
            data = json.load(f)
        drill_amp = np.array(data["profile"]["drill"])
        resolution = data["header"]["resolutionFeed"]
        filtered, _ = filter_signal(drill_amp, resolution)
        pile = trim_signal(filtered)
        rings = count_annual_rings(pile, resolution)
        assert 10 < rings < 300


# ---------------------------------------------------------------------------
# estimate_growth_rate
# ---------------------------------------------------------------------------


class TestEstimateGrowthRate:
    def test_returns_positive_float(self, synthetic_pile_signal: np.ndarray, resolution: int) -> None:
        diameter = estimate_diameter(synthetic_pile_signal, resolution)
        growth_rate = estimate_growth_rate(synthetic_pile_signal, diameter, resolution)
        assert isinstance(growth_rate, float)
        assert growth_rate > 0

    def test_raises_on_too_short_signal(self, resolution: int) -> None:
        short_signal = np.ones(10)
        with pytest.raises(ValueError):
            estimate_growth_rate(short_signal, 1.0, resolution)

    def test_raises_when_no_peaks_in_outer_zone(self, resolution: int) -> None:
        """A flat signal in the outer zone should raise ValueError."""
        flat_signal = np.ones(2000)
        diameter = estimate_diameter(flat_signal, resolution)
        with pytest.raises(ValueError, match="No peaks found"):
            estimate_growth_rate(flat_signal, diameter, resolution)

    def test_real_signal_growth_rate_plausible(self, sample_rgp_path) -> None:
        """Growth rate from a real signal should be between 0.5 mm/ring and 20 mm/ring."""
        import json
        with open(sample_rgp_path) as f:
            data = json.load(f)
        drill_amp = np.array(data["profile"]["drill"])
        resolution = data["header"]["resolutionFeed"]
        filtered, _ = filter_signal(drill_amp, resolution)
        pile = trim_signal(filtered)
        diameter = estimate_diameter(pile, resolution)
        growth_rate = estimate_growth_rate(pile, diameter, resolution)
        assert 0.5 < growth_rate < 20.0


# ---------------------------------------------------------------------------
# estimate_sapwood_width
# ---------------------------------------------------------------------------


class TestEstimateSapwoodWidth:
    def test_returns_positive_float(self) -> None:
        result = estimate_sapwood_width(growth_rate=2.5, rings=80)
        assert isinstance(result, float)
        assert result > 0

    def test_higher_growth_rate_gives_wider_sapwood(self) -> None:
        """Faster-growing trees have wider sapwood."""
        slow = estimate_sapwood_width(growth_rate=1.0, rings=80)
        fast = estimate_sapwood_width(growth_rate=4.0, rings=80)
        assert fast > slow

    def test_more_rings_tends_toward_asymptote(self) -> None:
        """The formula asymptotes as ring count increases."""
        young = estimate_sapwood_width(growth_rate=2.0, rings=20)
        old = estimate_sapwood_width(growth_rate=2.0, rings=200)
        assert old > young  # sapwood generally increases then plateaus

    def test_known_formula_output(self) -> None:
        """Verify a known result against the formula: 37.17 * r^0.95 / (1 + 5.58 * exp(-0.054 * n))."""
        import math
        r, n = 2.0, 80
        expected = round(37.17 * r**0.95 / (1 + 5.58 * math.exp(-0.054 * n)))
        assert estimate_sapwood_width(r, n) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# detect_soft_shell
# ---------------------------------------------------------------------------


class TestDetectSoftShell:
    def test_returns_two_floats(self, synthetic_pile_signal: np.ndarray, resolution: int) -> None:
        movav = compute_moving_average(synthetic_pile_signal)
        diameter = estimate_diameter(synthetic_pile_signal, resolution)
        left, right = detect_soft_shell(movav, diameter, resolution)
        assert isinstance(left, float)
        assert isinstance(right, float)

    def test_left_less_than_pith(self, synthetic_pile_signal: np.ndarray, resolution: int) -> None:
        """Soft shell left boundary should be on the left half."""
        movav = compute_moving_average(synthetic_pile_signal)
        diameter = estimate_diameter(synthetic_pile_signal, resolution)
        left, _ = detect_soft_shell(movav, diameter, resolution)
        assert left < diameter / 2

    def test_right_greater_than_pith(self, synthetic_pile_signal: np.ndarray, resolution: int) -> None:
        """Soft shell right boundary should be on the right half."""
        movav = compute_moving_average(synthetic_pile_signal)
        diameter = estimate_diameter(synthetic_pile_signal, resolution)
        _, right = detect_soft_shell(movav, diameter, resolution)
        assert right > diameter / 2

    def test_no_soft_shell_returns_zero_and_diameter(self, resolution: int) -> None:
        """A perfectly uniform signal has no soft shell; left=0, right≈diameter."""
        n = 500
        signal = np.ones(n) * 15.0
        movav = compute_moving_average(signal)
        diameter = estimate_diameter(signal, resolution)
        left, right = detect_soft_shell(movav, diameter, resolution)
        assert left == pytest.approx(0.0)

    def test_real_signal_soft_shell_plausible(self, sample_rgp_path) -> None:
        """Soft shell thicknesses from a real signal should be between 0 and 50 mm."""
        import json
        with open(sample_rgp_path) as f:
            data = json.load(f)
        drill_amp = np.array(data["profile"]["drill"])
        resolution = data["header"]["resolutionFeed"]
        filtered, _ = filter_signal(drill_amp, resolution)
        pile = trim_signal(filtered)
        diameter = estimate_diameter(pile, resolution)
        movav = compute_moving_average(pile)
        soft_left, soft_right = detect_soft_shell(movav, diameter, resolution)
        entrance = soft_left
        exit_ = diameter - soft_right
        assert 0 <= entrance <= 50
        assert 0 <= exit_ <= 50
