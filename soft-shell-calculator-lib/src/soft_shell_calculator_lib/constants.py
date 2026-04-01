"""A collection of all constants used by the signal processing algorithms."""

# --- Signal threshold filtering (Step 2) ---

SIGNAL_THRESHOLD_FRACTION: float = 0.01
"""Fraction of the signal average used as the lower threshold to filter out
near-zero samples before the drill bit enters the wood."""

# --- Variance-based trimming (Step 3) ---

VARIANCE_WINDOW_SIZE: int = 25
"""Number of samples in the sliding window used for variance-based trimming."""

VARIANCE_THRESHOLD: float = 0.01
"""Minimum variance required for a window to be considered part of the wood
cross-section signal."""

# --- Moving average (Step 6) ---

MOVING_AVERAGE_HALF_WINDOW: int = 50
"""Half-window size for the symmetric moving average (total window = 100 samples)."""

# --- Annual ring counting (Step 7) ---

SG_FILTER_WINDOW_LENGTH: int = 15
"""Window length for the Savitzky-Golay smoothing filter applied before peak detection."""

SG_FILTER_POLY_ORDER: int = 11
"""Polynomial order for the Savitzky-Golay smoothing filter."""

PEAK_MIN_DISTANCE_FRACTION: float = 0.1
"""Minimum distance between detected peaks as a fraction of the resolution.
Minimum peak distance in samples = PEAK_MIN_DISTANCE_FRACTION * resolution."""

# --- Growth rate estimation (Step 8) ---

GROWTH_RATE_OUTER_ZONE_FRACTION: float = 0.75
"""Fraction of the pile radius used as the outer zone for growth rate estimation.
Peaks are counted from the bark inward to this fraction of the radius,
avoiding the more compressed rings near the pith."""

# --- Sapwood width estimation (Step 9) ---
# Empirical regression formula: sapwood = A * growth_rate^B / (1 + C * exp(-D * rings))

SAPWOOD_COEFF_A: float = 37.17
SAPWOOD_COEFF_B: float = 0.95
SAPWOOD_COEFF_C: float = 5.58
SAPWOOD_COEFF_D: float = 0.054

# --- Soft shell detection (Step 10) ---

SOFT_SHELL_IOMA_THRESHOLD_FRACTION: float = 0.4
"""Fraction of the maximum IOMA value used as the threshold for detecting
the soft shell boundary. Positions where movav > fraction * max(IOMA)
are considered inside the sound wood zone."""

# --- Signal quality warnings ---

SOFT_SHELL_ASYMMETRY_WARNING_THRESHOLD: float = 0.5
"""Relative difference threshold above which a warning is raised when the
entrance and exit soft shell thicknesses differ. Reference: TUD-F8.1.20240813-GP."""

DRILL_AMPLITUDE_WARNING_THRESHOLD: float = 0.75
"""Fraction of the maximum possible drilling amplitude above which a signal
quality warning is raised. Reference: TUD-F8.1.20240813-GP."""
