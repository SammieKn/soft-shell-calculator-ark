"""Module defining the RPDMeasurement class.

Represents a single RPD (Resistograph Pile Drilling) measurement loaded from
one .rgp file. Holds raw data only; signal processing is handled by the
calculator module.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from soft_shell_calculator_lib.utils import MeasurementIdentifier, get_logger

logger = get_logger(__name__)


@dataclass
class RPDMeasurement:
    """A single RPD measurement loaded from one .rgp file.

    Holds the raw data read from the file. No signal processing is performed
    at this level; computation is handled by the calculator module.

    The ``identifier`` is parsed from the filename stem and gives structured
    access to the retaining wall, construction part, pile, and measurement
    IDs. These map directly onto the domain model hierarchy.

    Attributes:
        identifier: Structured identifier parsed from the filename, exposing
            ``retaining_wall_id``, ``construction_part_id``, ``pile_id``,
            and ``measurement_id``.
        date: Date on which the measurement was taken.
        resolution: Feed resolution in samples per mm
            (from ``header.resolutionFeed``).
        drill_signal: Raw drilling resistance values (%) sampled at each step.
    """

    identifier: MeasurementIdentifier
    date: datetime
    resolution: int
    drill_signal: list[float]

    @classmethod
    def from_rgp_file(cls, file_path: Path) -> "RPDMeasurement":
        """Load an RPDMeasurement from a .rgp file.

        The measurement identifier is parsed from the filename stem following
        the convention::

            <retaining_wall_id>_<construction_part_id>_<pile_id>_<measurement_id>

        Args:
            file_path: Path to the .rgp file to load.

        Returns:
            An RPDMeasurement populated with the data from the file.

        Raises:
            ValueError: If the file does not have a ``.rgp`` extension, or if
                the filename stem does not match the expected naming convention.
            FileNotFoundError: If the file does not exist.
            KeyError: If required fields are missing from the file header.
        """
        if file_path.suffix.lower() != ".rgp":
            raise ValueError(
                f"Expected a .rgp file, got '{file_path.suffix}': {file_path}"
            )

        with open(file_path, "r") as f:
            data = json.load(f)

        header = data["header"]
        measurement = cls(
            identifier=MeasurementIdentifier.from_filename_stem(file_path.stem),
            date=datetime(
                year=header["dateYear"],
                month=header["dateMonth"],
                day=header["dateDay"],
            ),
            resolution=header["resolutionFeed"],
            drill_signal=data["profile"]["drill"],
        )

        return measurement
