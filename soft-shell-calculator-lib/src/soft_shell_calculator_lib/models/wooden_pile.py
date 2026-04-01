from dataclasses import dataclass
from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement


@dataclass
class WoodenPile:
    id: str
    rpd_measurements: list[RPDMeasurement]

    @property
    def diameter(self) -> float:
        """the estimated diameter of the pile in cm"""
        pass

    @property
    def nuumber_of_annual_rings(self) -> int:
        """the estimated number of annual rings in the pile"""
        pass

    @property
    def sapwood_thickness(self) -> float:
        """the estimated thickness of the sapwood in cm"""
        pass

    @property
    def heartwood_thickness(self) -> float:
        """the estimated thickness of the heartwood in cm"""
        pass

    @property
    def soft_shell_entrance_thickness(self) -> float:
        """the estimated thickness of the soft shell entrance in cm"""
        pass

    @property
    def soft_shell_exit_thickness(self) -> float:
        """the estimated thickness of the soft shell exit in cm"""
        pass

    # TODO: implement warning if soft shell left differs >50% from soft shell right, then warning TUD-F8.1.20240813-GP
