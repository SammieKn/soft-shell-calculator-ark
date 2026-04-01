from dataclasses import dataclass
from soft_shell_calculator_lib.models.wooden_pile import WoodenPile


@dataclass
class ConstructionPart:
    id: str
    wooden_piles: list[WoodenPile]
