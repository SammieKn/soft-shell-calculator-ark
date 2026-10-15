"""A collection of utility functions for the soft shell calculator library."""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


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

    Note: The ``measurement_id`` in the filename (e.g. ``BM059``) and the
    header ``number`` (e.g. ``59``) are different representations of the same
    measurement. The header values (``idNumber`` and ``number``) are the
    primary source because they are more consistent; the filename is only
    used as a fallback.

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
    def from_rgp_file(
        cls,
        file_path: Path,
        id_number: str | None = None,
        measurement_number: int | str | None = None,
    ) -> "MeasurementIdentifier":
        """Parse a MeasurementIdentifier from an .rgp file.

        The header ``idNumber`` and ``number`` are the primary source. If they
        are missing or malformed, the filename stem is used instead.

        Args:
            file_path: Path to the .rgp file.
            id_number: The ``idNumber`` value from the file header, if present.
            measurement_number: The ``number`` value from the file header,
                if present.

        Returns:
            A MeasurementIdentifier with the four component IDs.

        Raises:
            ValueError: If neither the header nor the filename yields a
                valid identifier.
        """
        header_error: ValueError | None = None
        if id_number is not None and measurement_number is not None:
            try:
                return cls.from_id_number(id_number, measurement_number)
            except ValueError as e:
                header_error = e

        try:
            return cls.from_filename_stem(file_path.stem)
        except ValueError as filename_error:
            if header_error is None:
                raise
            raise ValueError(
                f"Failed to parse MeasurementIdentifier from file "
                f"'{file_path}' (expected format): "
                f"{header_error}; {filename_error}"
            ) from filename_error

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
    def from_id_number(
        cls, id_number: str, measurement_number: int | str
    ) -> "MeasurementIdentifier":
        """Parse a MeasurementIdentifier from a device idNumber and number.

        The measurement ID is taken from ``measurement_number``; any fourth
        component of ``id_number`` is ignored.

        Args:
            id_number: The ``idNumber`` value from the .rgp file header,
                e.g. ``"DYG0101/CON.A/P1.100/B"``.
            measurement_number: The ``number`` value from the .rgp file header,
                e.g. ``77``.

        Returns:
            A MeasurementIdentifier with the four component IDs.

        Raises:
            ValueError: If ``id_number`` does not split into 3 or 4 parts
                on ``/``.
        """
        parts = id_number.split("/")
        if len(parts) not in (3, 4):
            raise ValueError(
                f"idNumber '{id_number}' does not match the expected format "
                f"'<retaining_wall>/<construction_part>/<pile>(/<measurement>)'. "
                f"Found {len(parts)} part(s) after splitting on '/' instead of 3 or 4."
            )
        return cls(
            retaining_wall_id=parts[0],
            construction_part_id=parts[1],
            pile_id=parts[2],
            measurement_id=str(measurement_number),
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


def natural_sort_key(value: str) -> tuple:
    """Return a sort key for natural ordering of identifier strings.

    Splits the string into alternating text/numeric parts so that e.g.
    ``P1.2`` sorts before ``P1.11``.

    Args:
        value: Identifier string such as ``'P1.11'``.

    Returns:
        Tuple of alternating string/int parts for correct numeric ordering.
    """
    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
    )
