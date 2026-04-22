"""Signal processing and calculation logic for the soft shell calculator.

This module contains all numerical computation extracted from the TU Delft
script that cannot be expressed as a simple property of a domain model.
Functions are pure: they take data arrays and parameters as input and return
results. They have no dependency on UI, file I/O, or domain models.

File parsing belongs in ``RPDMeasurement.from_rgp_file``. The functions here
receive already-loaded signal data and resolution as arguments.
"""

import numpy as np
from scipy.signal import find_peaks, savgol_filter

from soft_shell_calculator_lib.constants import (
    GROWTH_RATE_OUTER_ZONE_FRACTION,
    MOVING_AVERAGE_HALF_WINDOW,
    PEAK_MIN_DISTANCE_FRACTION,
    SAPWOOD_COEFF_A,
    SAPWOOD_COEFF_B,
    SAPWOOD_COEFF_C,
    SAPWOOD_COEFF_D,
    SG_FILTER_POLY_ORDER,
    SG_FILTER_WINDOW_LENGTH,
    SIGNAL_THRESHOLD_FRACTION,
    SOFT_SHELL_IOMA_THRESHOLD_FRACTION,
    VARIANCE_THRESHOLD,
    VARIANCE_WINDOW_SIZE,
)


def filter_signal(
    drill_amp: np.ndarray,
    resolution: float,
) -> tuple[np.ndarray, float]:
    """Filter out near-zero samples from the raw drill signal.

    Removes samples below 1% of the signal average, which correspond to
    the period before the drill bit enters the wood. Also computes the
    depth at which the signal first exceeds the threshold.

    Args:
        drill_amp: Raw drilling resistance array (%) from the .rgp file.
        resolution: Feed resolution in samples per mm.

    Returns:
        A tuple of:
        - ``filtered_signal``: Array of samples above the threshold.
        - ``threshold_cut``: Depth in mm at which the threshold is first exceeded.

    Raises:
        ValueError: If no samples in the signal exceed the threshold.
    """
    threshold = SIGNAL_THRESHOLD_FRACTION * np.average(drill_amp)
    above_threshold = np.where(drill_amp > threshold)[0]

    if len(above_threshold) == 0:
        raise ValueError(
            "No samples in the drill signal exceed the threshold. "
            "The signal may be all-zero or too weak."
        )

    filtered_signal = drill_amp[drill_amp > threshold]
    threshold_cut = above_threshold[0] / resolution
    return filtered_signal, threshold_cut


def trim_signal(filtered_signal: np.ndarray) -> np.ndarray:
    """Trim the filtered signal to isolate the wood cross-section.

    Scans 25-sample windows across the signal. Windows with variance below
    0.01 (near-constant, indicating the lead-in or lead-out region outside
    the wood) are skipped one sample at a time. Once a high-variance window
    is found, all 25 samples are accepted and the index advances by 25.

    Args:
        filtered_signal: Filtered drill signal from ``filter_signal``.

    Returns:
        The trimmed pile signal representing only the wood cross-section.
    """
    pile_signal: list[float] = []
    i = 0

    while i < len(filtered_signal) - VARIANCE_WINDOW_SIZE:
        window = filtered_signal[i : i + VARIANCE_WINDOW_SIZE]
        if np.var(window) > VARIANCE_THRESHOLD:
            pile_signal.extend(window)
            i += VARIANCE_WINDOW_SIZE
        else:
            i += 1

    pile_signal.extend(filtered_signal[i:])
    return np.array(pile_signal)


def compute_overlap_position(
    drill_amp: np.ndarray,
    threshold_cut: float,
    resolution: float,
) -> float:
    """Find the depth offset for aligning the original and trimmed signals.

    Scans the original signal for the first 25-sample window with sufficient
    variance, then returns the maximum of the variance-based position and the
    threshold cut. Used only for plotting alignment.

    Args:
        drill_amp: Raw drilling resistance array (%) from the .rgp file.
        threshold_cut: Depth in mm returned by ``filter_signal``.
        resolution: Feed resolution in samples per mm.

    Returns:
        Depth offset in mm to align the original signal with the pile signal.
    """
    overlap_position = 0.0

    for p in range(len(drill_amp) - VARIANCE_WINDOW_SIZE):
        window = drill_amp[p : p + VARIANCE_WINDOW_SIZE]
        if np.var(window) > VARIANCE_THRESHOLD:
            overlap_position = p / resolution
            break

    return max(threshold_cut, overlap_position)


def estimate_diameter(pile_signal: np.ndarray, resolution: float) -> float:
    """Estimate the pile diameter from the length of the trimmed signal.

    Args:
        pile_signal: Trimmed pile signal from ``trim_signal``.
        resolution: Feed resolution in samples per mm.

    Returns:
        Estimated diameter in mm.
    """
    return len(pile_signal) / resolution


def compute_moving_average(pile_signal: np.ndarray) -> np.ndarray:
    """Compute a symmetric 100-sample moving average over the pile signal.

    Uses a window of 50 samples on each side of each position. At the edges
    of the signal the window is shortened symmetrically to avoid bias.

    Args:
        pile_signal: Trimmed pile signal from ``trim_signal``.

    Returns:
        Moving average array of the same length as ``pile_signal``.
    """
    n = len(pile_signal)
    movav = np.empty(n)

    for k in range(n):
        i = max(0, k - MOVING_AVERAGE_HALF_WINDOW)
        j = min(n, k + MOVING_AVERAGE_HALF_WINDOW)
        movav[k] = np.mean(pile_signal[i:j])

    return movav


def count_annual_rings(pile_signal: np.ndarray, resolution: float) -> int:
    """Estimate the number of annual growth rings.

    Smooths the pile signal with a Savitzky-Golay filter and counts peaks.
    The peak count is divided by 2 because the drill passes through the pith,
    crossing each ring twice (once entering, once exiting).

    Args:
        pile_signal: Trimmed pile signal from ``trim_signal``.
        resolution: Feed resolution in samples per mm.

    Returns:
        Estimated number of annual growth rings.

    Raises:
        ValueError: If the signal is too short for the Savitzky-Golay filter.
    """
    if len(pile_signal) <= SG_FILTER_WINDOW_LENGTH:
        raise ValueError(
            f"Pile signal (length {len(pile_signal)}) is too short for "
            f"Savitzky-Golay filter (window {SG_FILTER_WINDOW_LENGTH})."
        )

    smoothed = savgol_filter(pile_signal, SG_FILTER_WINDOW_LENGTH, SG_FILTER_POLY_ORDER)
    peaks, _ = find_peaks(smoothed, distance=PEAK_MIN_DISTANCE_FRACTION * resolution)
    return round(len(peaks) / 2)


def estimate_growth_rate(
    pile_signal: np.ndarray,
    diameter: float,
    resolution: float,
) -> float:
    """Estimate the average radial growth rate in mm per ring.

    Counts peaks in the outer 75% zone on each side of the pith to avoid
    the more compressed rings near the centre. The growth rate is the
    average of the left and right estimates.

    Args:
        pile_signal: Trimmed pile signal from ``trim_signal``.
        diameter: Estimated diameter in mm from ``estimate_diameter``.
        resolution: Feed resolution in samples per mm.

    Returns:
        Estimated growth rate in mm per ring.

    Raises:
        ValueError: If no peaks are found in either outer zone, which
            prevents a meaningful growth rate estimate.
    """
    if len(pile_signal) <= SG_FILTER_WINDOW_LENGTH:
        raise ValueError(
            f"Pile signal (length {len(pile_signal)}) is too short for "
            f"Savitzky-Golay filter (window {SG_FILTER_WINDOW_LENGTH})."
        )

    smoothed = savgol_filter(pile_signal, SG_FILTER_WINDOW_LENGTH, SG_FILTER_POLY_ORDER)
    radius = diameter / 2
    min_peak_distance = PEAK_MIN_DISTANCE_FRACTION * resolution

    outer_zone_end = int(GROWTH_RATE_OUTER_ZONE_FRACTION * radius * resolution)
    inner_zone_start = int((2 - GROWTH_RATE_OUTER_ZONE_FRACTION) * radius * resolution)

    peaks_left, _ = find_peaks(smoothed[:outer_zone_end], distance=min_peak_distance)
    peaks_right, _ = find_peaks(smoothed[inner_zone_start:], distance=min_peak_distance)

    n_left = len(peaks_left)
    n_right = len(peaks_right)

    if n_left == 0 or n_right == 0:
        raise ValueError(
            f"No peaks found in the outer zone of the pile signal "
            f"(left zone peaks: {n_left}, right zone peaks: {n_right}). "
            "Cannot estimate growth rate. Check signal quality."
        )

    zone_length = GROWTH_RATE_OUTER_ZONE_FRACTION * radius
    return (zone_length / n_left + zone_length / n_right) / 2


def estimate_sapwood_width(growth_rate: float, rings: int) -> float:
    """Estimate the sapwood width using an empirical regression formula.

    Formula:

    .. math::

        \\text{sapwood} = \\frac{A \\cdot r_g^B}{1 + C \\cdot e^{-D \\cdot \\text{rings}}}

    where :math:`r_g` is the growth rate in mm/ring.

    Args:
        growth_rate: Radial growth rate in mm per ring from
            ``estimate_growth_rate``.
        rings: Estimated number of annual rings from ``count_annual_rings``.

    Returns:
        Estimated sapwood width in mm, rounded to the nearest mm.
    """
    numerator = SAPWOOD_COEFF_A * growth_rate**SAPWOOD_COEFF_B
    denominator = 1 + SAPWOOD_COEFF_C * np.exp(-SAPWOOD_COEFF_D * rings)
    return float(round(numerator / denominator))


def detect_soft_shell(
    movav: np.ndarray,
    diameter: float,
    resolution: float,
) -> tuple[float, float]:
    """Detect the soft shell boundary positions using IOMA.

    Computes an Incremental One-directional Moving Average (IOMA) from the
    pith outward toward the bark on each side. The soft shell boundary is
    the position where the moving average falls below 40% of the maximum
    IOMA value, which represents the peak quality of the sound wood.

    Note: This implementation corrects two bugs in the original TU Delft
    script: the accumulator was incorrectly reset after each sample (making
    IOMA equivalent to movav), and ``ioma_left`` was reversed inside the
    right-side loop on every iteration.

    Args:
        movav: Moving average array from ``compute_moving_average``.
        diameter: Estimated diameter in mm from ``estimate_diameter``.
        resolution: Feed resolution in samples per mm.

    Returns:
        A tuple of:
        - ``soft_shell_left``: Distance from the entrance in mm.
        - ``soft_shell_right``: Distance from the entrance to the right
          boundary in mm (subtract from ``diameter`` to get exit thickness).
    """
    pith_idx = int(diameter / 2 * resolution)
    pith_idx = min(pith_idx, len(movav) - 1)

    # Left IOMA: cumulative mean from pith outward toward the bark (left side).
    # Iterating in reversed order (pith → bark), then reversing result to
    # restore bark → pith indexing aligned with movav.
    left_half_pith_to_bark = movav[:pith_idx][::-1]
    counts = np.arange(1, len(left_half_pith_to_bark) + 1)
    ioma_left = (np.cumsum(left_half_pith_to_bark) / counts)[::-1]

    # Right IOMA: cumulative mean from pith outward toward the bark (right side).
    right_half = movav[pith_idx:]
    counts_right = np.arange(1, len(right_half) + 1)
    ioma_right = np.cumsum(right_half) / counts_right

    threshold_left = SOFT_SHELL_IOMA_THRESHOLD_FRACTION * np.max(ioma_left)
    threshold_right = SOFT_SHELL_IOMA_THRESHOLD_FRACTION * np.max(ioma_right)

    above_left = np.where(movav > threshold_left)[0]
    above_right = np.where(movav > threshold_right)[0]

    soft_shell_left = (
        float(above_left.min() / resolution) if len(above_left) > 0 else 0.0
    )
    soft_shell_right = (
        float(above_right.max() / resolution) if len(above_right) > 0 else diameter
    )

    return soft_shell_left, soft_shell_right
