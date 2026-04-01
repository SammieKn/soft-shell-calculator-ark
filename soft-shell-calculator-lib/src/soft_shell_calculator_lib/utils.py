"""A collection of utility functions for the soft shell calculator library."""

import difflib
import logging
from typing import Optional


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


def pair_similar_names(
    names: list[str],
    threshold: float = 0.8,
) -> list[tuple[str, str]]:
    """Pair names that are similar enough to represent the same pole.

    Uses ``difflib.SequenceMatcher`` similarity to find pairs of filenames
    that likely represent two RPD drill passes from opposite sides of the
    same wooden pile. Each name is used in at most one pair.

    Args:
        names: List of measurement identifiers or filenames to pair.
        threshold: Minimum similarity ratio (0.0–1.0) for a pair to be
            accepted. Defaults to 0.8.

    Returns:
        A list of ``(name1, name2)`` tuples for each identified pair.
    """
    pairs: list[tuple[str, str]] = []
    used: set[str] = set()

    for i, name1 in enumerate(names):
        if name1 in used:
            continue
        for name2 in names[i + 1 :]:
            if name2 in used:
                continue
            similarity = difflib.SequenceMatcher(None, name1, name2).ratio()
            if similarity >= threshold:
                pairs.append((name1, name2))
                used.add(name1)
                used.add(name2)
                break

    return pairs
