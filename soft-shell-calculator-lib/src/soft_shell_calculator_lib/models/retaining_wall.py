from dataclasses import dataclass
from soft_shell_calculator_lib.models.construction_part import ConstructionPart


@dataclass
class RetainingWall:
    id: str
    construction_parts: list[ConstructionPart]
