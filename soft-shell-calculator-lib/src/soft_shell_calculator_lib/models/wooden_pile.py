"""Module defining the WoodenPile class and related internal types."""

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from soft_shell_calculator_lib.utils import get_logger

logger = get_logger(__name__)


class _MeasurementResult(NamedTuple):
    """Computed results for a single RPD measurement."""

    diameter: float
    rings: int
    sapwood_thickness: float
    soft_shell_entrance: float
    soft_shell_exit: float


@dataclass
class WoodenPile:
    """A wooden foundation pile with one or two RPD measurements.

    A pile normally has two RPDMeasurement objects representing drill passes
    from opposite sides. Properties compute estimates by running the signal
    processing pipeline per measurement and averaging the results.

    Attributes:
        id: Identifier for this pile.
        rpd_measurements: One or two measurements taken from this pile.
    """

    id: str
    rpd_measurements: list[RPDMeasurement]

    def _get_results(self) -> list[_MeasurementResult]:
        """Process all measurements and return their computed results.

        Returns:
            List of computed results, one entry per measurement.

        Raises:
            ValueError: If the pile has no RPD measurements.
        """
        # Import here to avoid a module-level circular dependency risk
        # (calculator imports nothing from models).
        from soft_shell_calculator_lib.calculator import (
            compute_moving_average,
            count_annual_rings,
            detect_soft_shell,
            estimate_diameter,
            estimate_growth_rate,
            estimate_sapwood_width,
            filter_signal,
            trim_signal,
        )

        if not self.rpd_measurements:
            raise ValueError(f"Pile '{self.id}' has no RPD measurements.")

        results = []
        for measurement in self.rpd_measurements:
            drill_amp = np.array(measurement.drill_signal)
            resolution = measurement.resolution

            filtered, _ = filter_signal(drill_amp, resolution)
            pile = trim_signal(filtered)
            diameter = estimate_diameter(pile, resolution)
            movav = compute_moving_average(pile)
            rings = count_annual_rings(pile, resolution)
            growth_rate = estimate_growth_rate(pile, diameter, resolution)
            sapwood = estimate_sapwood_width(growth_rate, rings)
            soft_left, soft_right = detect_soft_shell(movav, diameter, resolution)

            results.append(
                _MeasurementResult(
                    diameter=diameter,
                    rings=rings,
                    sapwood_thickness=sapwood,
                    soft_shell_entrance=soft_left,
                    soft_shell_exit=diameter - soft_right,
                )
            )
        return results

    @property
    def diameter(self) -> float:
        """Estimated diameter of the pile in mm.

        Returns:
            Average diameter across all measurements in mm.
        """
        results = self._get_results()
        return sum(r.diameter for r in results) / len(results)

    @property
    def number_of_annual_rings(self) -> int:
        """Estimated number of annual growth rings.

        Returns:
            Average ring count across all measurements, rounded to nearest integer.
        """
        results = self._get_results()
        return round(sum(r.rings for r in results) / len(results))

    @property
    def sapwood_thickness(self) -> float:
        """Estimated thickness of the sapwood layer in mm.

        Returns:
            Average sapwood thickness across all measurements in mm.
        """
        results = self._get_results()
        return sum(r.sapwood_thickness for r in results) / len(results)

    @property
    def heartwood_thickness(self) -> float:
        """Estimated thickness of the heartwood (inner core) in mm.

        Derived as pile radius minus sapwood thickness. Not independently
        estimated from the signal.

        Returns:
            Heartwood thickness in mm.
        """
        return self.diameter / 2 - self.sapwood_thickness

    @property
    def soft_shell_entrance_thickness(self) -> float:
        """Estimated soft shell thickness on the drill entrance side in mm.

        Returns:
            Average soft shell entrance thickness across all measurements in mm.
        """
        results = self._get_results()
        return sum(r.soft_shell_entrance for r in results) / len(results)

    @property
    def soft_shell_exit_thickness(self) -> float:
        """Estimated soft shell thickness on the drill exit side in mm.

        Returns:
            Average soft shell exit thickness across all measurements in mm.
        """
        results = self._get_results()
        return sum(r.soft_shell_exit for r in results) / len(results)

    def validate(self) -> None:
        """Log warnings for any detected signal quality issues.

        Checks for soft shell asymmetry: warns if the entrance and exit
        soft shell thicknesses differ by more than 50%.
        Reference: TUD-F8.1.20240813-GP.
        """
        from soft_shell_calculator_lib.constants import (
            SOFT_SHELL_ASYMMETRY_WARNING_THRESHOLD,
        )

        results = self._get_results()
        entrance = sum(r.soft_shell_entrance for r in results) / len(results)
        exit_ = sum(r.soft_shell_exit for r in results) / len(results)
        max_val = max(entrance, exit_)
        if max_val > 0:
            relative_diff = abs(entrance - exit_) / max_val
            if relative_diff > SOFT_SHELL_ASYMMETRY_WARNING_THRESHOLD:
                logger.warning(
                    "Soft shell asymmetry detected for pile '%s': "
                    "entrance=%.1f mm, exit=%.1f mm (%.0f%% relative difference). "
                    "Reference: TUD-F8.1.20240813-GP.",
                    self.id,
                    entrance,
                    exit_,
                    relative_diff * 100,
                )
