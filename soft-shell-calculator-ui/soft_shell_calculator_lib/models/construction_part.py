"""Module defining the ConstructionPart class."""

from dataclasses import dataclass

from soft_shell_calculator_lib.models.wooden_pile import WoodenPile


@dataclass
class ConstructionPart:
    """A construction part of a retaining wall, containing one or more wooden piles.

    Attributes:
        id: Identifier for this construction part (e.g. 'CON.A').
        wooden_piles: List of wooden piles belonging to this construction part.
    """

    id: str
    wooden_piles: list[WoodenPile]
