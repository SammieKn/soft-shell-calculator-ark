"""
The goal of this module is to define the RPDMeasurement class, which represents a measurement of the individual RPD signal.
It is related to a wooden pile.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RPDMeasurement:
    id: str
    date: datetime

    # TODO: implement if drilling amplitude in signal >75%, then warning TUD-F8.1.20240813-GP
    @classmethod
    def from_rgp_file(cls, file_path: Path) -> RPDMeasurement:
        # should return the RPD measurement
        # check if the file is a correct type else raise error
        pass
