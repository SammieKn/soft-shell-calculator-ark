"""A collection of utility functions for the soft shell calculator library."""

import logging
from collections import defaultdict
from dataclasses import dataclass


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name.

    Following Python library conventions, a NullHandler is added if no
    handlers have been configured. Log handlers and formatting should be
    configured by the consuming application, not the library.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A Logger instance with a NullHandler if no handlers exist.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


@dataclass(frozen=True)
class MeasurementIdentifier:
    """Structured identifier for an RPD measurement parsed from a filename or idNumber.

    The naming convention used in .rgp filenames is::

        <retaining_wall_id>_<construction_part_id>_<pile_id>_<measurement_id>

    For example: ``DYG0101_CON.A_P1.100_BM059``

    The device's ``idNumber`` field in the .rgp header uses the same four
    components separated by ``/``::

        DYG0101/CON.A/P1.100/B

    Note: The ``measurement_id`` in the filename (e.g. ``BM059``) and in
    the ``idNumber`` (e.g. ``B``) are different representations of the same
    measurement. The filename form is more specific and is the primary source.

    Attributes:
        retaining_wall_id: Identifier of the retaining wall.
        construction_part_id: Identifier of the construction part within the wall.
        pile_id: Identifier of the wooden pile within the construction part.
        measurement_id: Identifier of the individual drill pass on the pile.
    """

    retaining_wall_id: str
    construction_part_id: str
    pile_id: str
    measurement_id: str

    @classmethod
    def from_filename_stem(cls, stem: str) -> "MeasurementIdentifier":
        """Parse a MeasurementIdentifier from a .rgp filename stem.

        Args:
            stem: Filename without extension,
                e.g. ``"DYG0101_CON.A_P1.100_BM059"``.

        Returns:
            A MeasurementIdentifier with the four component IDs.

        Raises:
            ValueError: If the stem does not split into exactly 4 parts on ``_``.
        """
        parts = stem.split("_", maxsplit=3)
        if len(parts) != 4:
            raise ValueError(
                f"Filename stem '{stem}' does not match the expected format "
                f"'<retaining_wall>_<construction_part>_<pile>_<measurement>'. "
                f"Found {len(parts)} part(s) after splitting on '_' instead of 4."
            )
        return cls(
            retaining_wall_id=parts[0],
            construction_part_id=parts[1],
            pile_id=parts[2],
            measurement_id=parts[3],
        )

    @classmethod
    def from_id_number(cls, id_number: str) -> "MeasurementIdentifier":
        """Parse a MeasurementIdentifier from a device idNumber string.

        Args:
            id_number: The ``idNumber`` value from the .rgp file header,
                e.g. ``"DYG0101/CON.A/P1.100/B"``.

        Returns:
            A MeasurementIdentifier with the four component IDs.

        Raises:
            ValueError: If the string does not split into exactly 4 parts on ``/``.
        """
        parts = id_number.split("/")
        if len(parts) != 4:
            raise ValueError(
                f"idNumber '{id_number}' does not match the expected format "
                f"'<retaining_wall>/<construction_part>/<pile>/<measurement>'. "
                f"Found {len(parts)} part(s) after splitting on '/' instead of 4."
            )
        return cls(
            retaining_wall_id=parts[0],
            construction_part_id=parts[1],
            pile_id=parts[2],
            measurement_id=parts[3],
        )

    @property
    def pile_key(self) -> tuple[str, str, str]:
        """Return the key that uniquely identifies a wooden pile.

        Two measurements share the same ``pile_key`` if and only if they were
        taken from the same pile (same retaining wall, construction part,
        and pile), regardless of their individual ``measurement_id``.

        Returns:
            Tuple of ``(retaining_wall_id, construction_part_id, pile_id)``.
        """
        return (self.retaining_wall_id, self.construction_part_id, self.pile_id)


def pair_measurements(names: list[str]) -> list[tuple[str, str]]:
    """Pair measurement filename stems that belong to the same wooden pile.

    Two measurements are paired when their filename stems share the same
    ``retaining_wall_id``, ``construction_part_id``, and ``pile_id`` but
    differ only in ``measurement_id``. This corresponds to two RPD drill
    passes taken from opposite sides of the same pile.

    Names that cannot be parsed and piles with more than two measurements
    are skipped with a warning.

    Args:
        names: List of .rgp filename stems (without extension) to pair.

    Returns:
        A list of ``(name1, name2)`` tuples, one per identified pair.
    """
    logger = get_logger(__name__)
    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    for name in names:
        try:
            identifier = MeasurementIdentifier.from_filename_stem(name)
            groups[identifier.pile_key].append(name)
        except ValueError:
            logger.warning(
                "Could not parse measurement identifier from '%s'; "
                "skipping for pairing.",
                name,
            )

    pairs: list[tuple[str, str]] = []
    for pile_key, group_names in groups.items():
        if len(group_names) == 2:
            pairs.append((group_names[0], group_names[1]))
        elif len(group_names) > 2:
            logger.warning(
                "Expected at most 2 measurements for pile %s, found %d: %s. "
                "Cannot pair automatically.",
                pile_key,
                len(group_names),
                group_names,
            )

    return pairs
