"""Upload and input parsing service for the VIKTOR app.

This module validates uploaded files, extracts zip archives to a temporary
working directory, and builds the retaining-wall domain object used by the UI.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import BadZipFile, ZipFile

from soft_shell_calculator_lib.models.retaining_wall import RetainingWall
from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from soft_shell_calculator_lib.utils import MeasurementIdentifier


@dataclass(frozen=True)
class UploadedMeasurements:
    """Contain the domain object and upload metadata.

    Attributes:
        source_filename: Name of the uploaded file.
        retaining_wall: Assembled retaining wall domain object.
        uploaded_rgp_count: Number of `.rgp` files found in the upload.
        valid_rgp_count: Number of valid `.rgp` files used in the analysis.
        skipped_files: Filenames skipped during validation.
    """

    source_filename: str
    retaining_wall: RetainingWall
    uploaded_rgp_count: int
    valid_rgp_count: int
    skipped_files: tuple[str, ...]


def load_uploaded_measurements(uploaded_file: Any) -> UploadedMeasurements:
    """Build a retaining wall from an uploaded zip or `.rgp` file.

    Args:
        uploaded_file: VIKTOR `FileResource`-like object with `filename` and `file`.

    Returns:
        Uploaded measurements with wall object and validation metadata.

    Raises:
        ValueError: If no file is provided or the file cannot be processed.
    """
    if uploaded_file is None:
        raise ValueError("Geen meetbestand geupload.")

    source_filename = _get_source_filename(uploaded_file)
    file_bytes = _read_uploaded_bytes(uploaded_file)

    with TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        uploaded_rgp_count = _materialize_upload(source_filename, file_bytes, temp_dir)
        skipped_files = _collect_skipped_files(temp_dir)
        retaining_wall = RetainingWall.from_directory(temp_dir)

    return UploadedMeasurements(
        source_filename=source_filename,
        retaining_wall=retaining_wall,
        uploaded_rgp_count=uploaded_rgp_count,
        valid_rgp_count=uploaded_rgp_count - len(skipped_files),
        skipped_files=skipped_files,
    )


def _get_source_filename(uploaded_file: Any) -> str:
    """Return the filename of the uploaded file resource.

    Args:
        uploaded_file: Uploaded VIKTOR file resource.

    Returns:
        Original filename.
    """
    filename = getattr(uploaded_file, "filename", "")
    if not filename:
        raise ValueError("Het geuploade bestand heeft geen geldige bestandsnaam.")
    return filename


def _read_uploaded_bytes(uploaded_file: Any) -> bytes:
    """Read all bytes from the uploaded VIKTOR file resource.

    Args:
        uploaded_file: Uploaded VIKTOR file resource.

    Returns:
        Raw file bytes.
    """
    if hasattr(uploaded_file, "open_binary"):
        with uploaded_file.open_binary() as file_handle:
            return file_handle.read()

    file_object = getattr(uploaded_file, "file", None)
    if file_object is None:
        raise ValueError("Het geuploade bestand kan niet worden gelezen.")

    if hasattr(file_object, "open_binary"):
        with file_object.open_binary() as file_handle:
            return file_handle.read()

    if hasattr(file_object, "getvalue"):
        file_value = file_object.getvalue()
        return file_value.encode("utf-8") if isinstance(file_value, str) else file_value

    if hasattr(file_object, "read"):
        file_value = file_object.read()
        return file_value.encode("utf-8") if isinstance(file_value, str) else file_value

    raise ValueError("Het geuploade bestand kan niet worden gelezen.")


def _materialize_upload(
    source_filename: str, file_bytes: bytes, target_dir: Path
) -> int:
    """Write uploaded `.rgp` content into a temporary directory.

    Args:
        source_filename: Original upload filename.
        file_bytes: Raw uploaded bytes.
        target_dir: Temporary target directory.

    Returns:
        Number of `.rgp` files written to the target directory.

    Raises:
        ValueError: If the upload format is unsupported or invalid.
    """
    suffix = Path(source_filename).suffix.lower()

    if suffix == ".zip":
        return _extract_zip_archive(file_bytes, target_dir)

    if suffix == ".rgp":
        (target_dir / Path(source_filename).name).write_bytes(file_bytes)
        return 1

    raise ValueError("Upload een zip-bestand of een .rgp-bestand.")


def _extract_zip_archive(file_bytes: bytes, target_dir: Path) -> int:
    """Extract `.rgp` files from a zip archive into a flat temp directory.

    Args:
        file_bytes: Raw zip bytes.
        target_dir: Temporary extraction directory.

    Returns:
        Number of `.rgp` files extracted.

    Raises:
        ValueError: If the zip archive is invalid or contains no `.rgp` files.
    """
    written_files = 0
    used_names: set[str] = set()

    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue

                member_name = Path(member.filename)
                if member_name.suffix.lower() != ".rgp":
                    continue

                safe_name = _deduplicate_filename(member_name.name, used_names)
                target_path = target_dir / safe_name

                with archive.open(member) as source:
                    target_path.write_bytes(source.read())

                written_files += 1
    except BadZipFile as exc:
        raise ValueError("Het geuploade zip-bestand is ongeldig.") from exc

    if written_files == 0:
        raise ValueError("Het zip-bestand bevat geen .rgp-bestanden.")

    return written_files


def _deduplicate_filename(filename: str, used_names: set[str]) -> str:
    """Return a unique filename for flattened zip extraction.

    Args:
        filename: Candidate filename.
        used_names: Filenames already used in the extraction directory.

    Returns:
        Unique filename.
    """
    candidate = filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1

    while candidate in used_names:
        candidate = f"{stem}_{counter}{suffix}"
        counter += 1

    used_names.add(candidate)
    return candidate


def _collect_skipped_files(target_dir: Path) -> tuple[str, ...]:
    """Return filenames that cannot be parsed as valid measurements.

    Args:
        target_dir: Temporary directory containing `.rgp` files.

    Returns:
        Sorted tuple of skipped filenames.
    """
    skipped_files: list[str] = []
    for rgp_file in sorted(target_dir.glob("*.rgp")):
        try:
            RPDMeasurement.from_rgp_file(rgp_file)
        except (ValueError, KeyError):
            skipped_files.append(rgp_file.name)

    return tuple(skipped_files)


def peek_wall_id_from_file_resource(uploaded_file: Any) -> str | None:
    """Extract the retaining-wall ID from a zip file resource without full analysis.

    Reads the first `.rgp` filename from the zip and parses the wall ID from its
    stem. Avoids loading any measurement data or constructing domain objects.

    Args:
        uploaded_file: VIKTOR FileResource-like object.

    Returns:
        Retaining wall ID or ``None`` if it cannot be determined.
    """
    try:
        file_bytes = _read_uploaded_bytes(uploaded_file)
        with ZipFile(BytesIO(file_bytes)) as archive:
            for name in archive.namelist():
                if name.lower().endswith(".rgp"):
                    stem = Path(name).stem
                    identifier = MeasurementIdentifier.from_filename_stem(stem)
                    return identifier.retaining_wall_id
    except Exception:
        return None
    return None
