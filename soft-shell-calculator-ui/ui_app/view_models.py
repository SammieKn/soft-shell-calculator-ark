"""UI-facing data structures for the VIKTOR app.

This module defines typed result models that bridge the reusable calculation
library to VIKTOR views and downloadable exports.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WallSummary:
    """Summarize the uploaded dataset at wall level.

    Attributes:
        source_filename: Name of the uploaded file.
        retaining_wall_id: Identifier of the retaining wall.
        construction_part_count: Number of construction parts in the dataset.
        pile_count: Number of unique piles in the dataset.
        measurement_count: Number of valid measurements used in the analysis.
        valid_file_count: Number of valid `.rgp` files in the upload.
        skipped_files: Filenames skipped during validation.
        failed_pile_count: Number of piles that could not be analyzed.
        warning_pile_count: Number of piles with non-fatal warnings.
    """

    source_filename: str
    retaining_wall_id: str
    construction_part_count: int
    pile_count: int
    measurement_count: int
    valid_file_count: int
    skipped_files: tuple[str, ...]
    failed_pile_count: int
    warning_pile_count: int


@dataclass(frozen=True)
class PileRow:
    """Represent one row in the pile-level result table.

    Attributes:
        retaining_wall_id: Identifier of the retaining wall.
        construction_part_id: Identifier of the construction part.
        pile_id: Identifier of the pile.
        measurement_ids: Identifiers of the measurements belonging to the pile.
        measurement_count: Number of measurements belonging to the pile.
        diameter_mm: Estimated average diameter in mm.
        annual_rings: Estimated average number of annual rings.
        sapwood_thickness_mm: Estimated average sapwood thickness in mm.
        heartwood_thickness_mm: Estimated average heartwood thickness in mm.
        soft_shell_entrance_mm: Estimated soft shell thickness on the entrance side in mm.
        soft_shell_exit_mm: Estimated soft shell thickness on the exit side in mm.
        high_drill_amplitude: Whether the pile exceeds the drill amplitude remark threshold.
        asymmetric_soft_shell: Whether the pile has asymmetric soft shell.
        warnings: User-facing warning messages for the pile.
        status: Status label shown in the UI.
        error_message: User-facing error text when the pile analysis failed.
    """

    retaining_wall_id: str
    construction_part_id: str
    pile_id: str
    measurement_ids: tuple[str, ...]
    measurement_count: int
    diameter_mm: float | None
    annual_rings: int | None
    sapwood_thickness_mm: float | None
    heartwood_thickness_mm: float | None
    soft_shell_entrance_mm: float | None
    soft_shell_exit_mm: float | None
    high_drill_amplitude: bool
    asymmetric_soft_shell: bool
    warnings: tuple[str, ...]
    status: str
    error_message: str | None


@dataclass(frozen=True)
class BatchAnalysisResult:
    """Bundle analysis results for multiple uploaded retaining walls.

    Attributes:
        wall_results: Per-wall analysis results, in upload order.
        skipped_walls: Source filenames of uploads that could not be analyzed.
    """

    wall_results: tuple["WallAnalysisResult", ...]
    skipped_walls: tuple[str, ...]


@dataclass(frozen=True)
class WallAnalysisResult:
    """Bundle all app-facing analysis results for one upload.

    Attributes:
        summary: Wall-level summary information.
        pile_rows: Flat pile-level rows for views and exports.
    """

    summary: WallSummary
    pile_rows: tuple[PileRow, ...]
