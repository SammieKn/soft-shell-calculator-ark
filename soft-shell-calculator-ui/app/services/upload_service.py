"""Upload and input parsing service for the VIKTOR app.

This module should validate uploaded files, extract zip archives to a
temporary working directory, and build domain objects from the uploaded
measurement set.
"""

from pathlib import Path


def get_upload_root() -> Path:
    """Return the placeholder upload root used during scaffolding.

    Returns:
        Placeholder path for future upload-processing logic.
    """
    return Path(".")
