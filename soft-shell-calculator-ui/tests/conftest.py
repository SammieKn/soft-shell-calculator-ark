"""Pytest configuration and shared fixtures for soft-shell-calculator-lib tests."""

from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data" / "IML DYG0101"


# ---------------------------------------------------------------------------
# File fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sample_rgp_path() -> Path:
    """Return the path to one sample .rgp file from the test dataset."""
    rgp_files = sorted(DATA_DIR.glob("*.rgp"))
    if not rgp_files:
        pytest.skip(f"No .rgp files found in {DATA_DIR}")
    return rgp_files[0]


@pytest.fixture(scope="session")
def all_rgp_paths() -> list[Path]:
    """Return all .rgp file paths from the test dataset."""
    rgp_files = sorted(DATA_DIR.glob("*.rgp"))
    if not rgp_files:
        pytest.skip(f"No .rgp files found in {DATA_DIR}")
    return rgp_files


# ---------------------------------------------------------------------------
# Synthetic signal fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resolution() -> int:
    """Standard resolution value (samples per mm) matching the test dataset."""
    return 10


@pytest.fixture
def synthetic_pile_signal(resolution: int) -> np.ndarray:
    """A synthetic pile signal that mimics real pile characteristics.

    Creates a signal of ~200 mm diameter with oscillating amplitude to
    simulate annual rings and a lower-amplitude region at both ends to
    simulate soft shell zones.
    """
    rng = np.random.default_rng(42)
    n_samples = 200 * resolution  # 200 mm at given resolution

    # Base oscillation simulating annual rings (period ~10 mm = 100 samples)
    x = np.linspace(0, 40 * np.pi, n_samples)
    base = 15 + 8 * np.sin(x)

    # Soft shell zones: reduce amplitude at 0–15% and 85–100% of the signal
    soft_zone = int(0.15 * n_samples)
    envelope = np.ones(n_samples)
    envelope[:soft_zone] = np.linspace(0.2, 1.0, soft_zone)
    envelope[-soft_zone:] = np.linspace(1.0, 0.2, soft_zone)

    signal = base * envelope + rng.normal(0, 0.5, n_samples)
    return signal.clip(min=0.1)


@pytest.fixture
def synthetic_drill_amp(
    synthetic_pile_signal: np.ndarray, resolution: int
) -> np.ndarray:
    """A synthetic raw drill signal with near-zero lead-in and lead-out."""
    lead = np.zeros(50)  # 5 mm of silence before / after
    return np.concatenate([lead, synthetic_pile_signal, lead])
