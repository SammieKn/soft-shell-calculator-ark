"""Module defining the RetainingWall class."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from soft_shell_calculator_lib.models.construction_part import ConstructionPart
from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from soft_shell_calculator_lib.models.wooden_pile import WoodenPile
from soft_shell_calculator_lib.utils import get_logger

logger = get_logger(__name__)


@dataclass
class RetainingWall:
    """A retaining wall composed of construction parts, each containing wooden piles.

    Attributes:
        id: Identifier for this retaining wall (e.g. 'DYG0101').
        construction_parts: List of construction parts belonging to this wall.
    """

    id: str
    construction_parts: list[ConstructionPart]

    @classmethod
    def from_directory(cls, path: Path) -> RetainingWall:
        """Load a RetainingWall from a directory of .rgp measurement files.

        When the directory contains files from multiple retaining walls, only
        the first wall (alphabetically by ID) is returned. Use
        :meth:`from_directory_multi` to obtain all walls.

        Args:
            path: Directory containing .rgp measurement files.

        Returns:
            A fully assembled RetainingWall instance.

        Raises:
            ValueError: If no valid .rgp files are found in the directory.
        """
        walls = cls.from_directory_multi(path)
        if len(walls) > 1:
            wall_ids = [w.id for w in walls]
            logger.warning(
                "Multiple retaining walls found in '%s': %s. "
                "Use from_directory_multi() to obtain all walls. "
                "Returning the first wall ('%s').",
                path,
                wall_ids,
                walls[0].id,
            )
        return walls[0]

    @classmethod
    def from_directory_multi(cls, path: Path) -> list[RetainingWall]:
        """Load one RetainingWall per unique wall ID from a directory of .rgp files.

        Scans the directory for all .rgp files, loads each as an RPDMeasurement,
        groups them first by ``retaining_wall_id``, then into WoodenPiles and
        ConstructionParts within each wall group.

        Files whose names do not follow the naming convention are skipped with
        a warning.

        Args:
            path: Directory containing .rgp measurement files.

        Returns:
            List of RetainingWall instances, one per unique retaining-wall ID,
            sorted alphabetically by wall ID.

        Raises:
            ValueError: If no .rgp files are found or no valid measurements
                could be loaded from the directory.
        """
        rgp_files = sorted(path.glob("*.rgp"))
        if not rgp_files:
            raise ValueError(f"No .rgp files found in '{path}'.")

        # Load measurements, skipping files with malformed names or content
        measurements: list[RPDMeasurement] = []
        for rgp_file in rgp_files:
            try:
                measurements.append(RPDMeasurement.from_rgp_file(rgp_file))
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping '%s': %s", rgp_file.name, exc)

        if not measurements:
            raise ValueError(f"No valid measurements could be loaded from '{path}'.")

        # Group measurements by retaining_wall_id
        wall_measurement_groups: dict[str, list[RPDMeasurement]] = defaultdict(list)
        for m in measurements:
            wall_measurement_groups[m.identifier.retaining_wall_id].append(m)

        walls: list[RetainingWall] = []
        for wall_id, wall_measurements in sorted(wall_measurement_groups.items()):
            # Group measurements by pile key → WoodenPile
            pile_groups: dict[tuple[str, str, str], list[RPDMeasurement]] = defaultdict(
                list
            )
            for m in wall_measurements:
                pile_groups[m.identifier.pile_key].append(m)

            # Group WoodenPiles by construction_part_id → ConstructionPart
            part_groups: dict[str, list[WoodenPile]] = defaultdict(list)
            for pile_key, pile_measurements in pile_groups.items():
                _, construction_part_id, pile_id = pile_key
                pile = WoodenPile(id=pile_id, rpd_measurements=pile_measurements)
                part_groups[construction_part_id].append(pile)

            construction_parts = [
                ConstructionPart(id=part_id, wooden_piles=piles)
                for part_id, piles in sorted(part_groups.items())
            ]
            walls.append(cls(id=wall_id, construction_parts=construction_parts))

        return walls
