"""Module defining the RPDMeasurement class.

Represents a single RPD (Resistograph Pile Drilling) measurement loaded from
one .rgp file. Holds raw data only; signal processing is handled by the
calculator module.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from soft_shell_calculator_lib.utils import get_logger

logger = get_logger(__name__)


@dataclass
class RPDMeasurement:
    """A single RPD measurement loaded from one .rgp file.

    Holds the raw data read from the file. No signal processing is performed
    at this level; computation is handled by the calculator module.

    Attributes:
        id: Identifier derived from the .rgp filename stem.
        id_number: Device-assigned identifier from the file header
            (e.g. ``"DYG0101/CON.A/P1.1/B"``).
        date: Date on which the measurement was taken.
        resolution: Feed resolution in samples per mm
            (from ``header.resolutionFeed``).
        drill_signal: Raw drilling resistance values (%) sampled at each step.
    """

    id: str
    id_number: str
    date: datetime
    resolution: int
    drill_signal: list[float]

    @classmethod
    def from_rgp_file(cls, file_path: Path) -> "RPDMeasurement":
        """Load an RPDMeasurement from a .rgp file.

        Args:
            file_path: Path to the .rgp file to load.

        Returns:
            An RPDMeasurement populated with the data from the file.

        Raises:
            ValueError: If the file does not have a ``.rgp`` extension.
            FileNotFoundError: If the file does not exist.
            KeyError: If required fields are missing from the file.
        """
        if file_path.suffix.lower() != ".rgp":
            raise ValueError(
                f"Expected a .rgp file, got '{file_path.suffix}': {file_path}"
            )

        with open(file_path, "r") as f:
            data = json.load(f)

        header = data["header"]
        measurement = cls(
            id=file_path.stem,
            id_number=header["idNumber"],
            date=datetime(
                year=header["dateYear"],
                month=header["dateMonth"],
                day=header["dateDay"],
            ),
            resolution=header["resolutionFeed"],
            drill_signal=data["profile"]["drill"],
        )

        # TODO: implement warning if drilling amplitude in signal >75%,
        # then warning TUD-F8.1.20240813-GP

        return measurement
