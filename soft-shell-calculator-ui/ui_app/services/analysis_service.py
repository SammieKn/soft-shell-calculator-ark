"""Analysis orchestration service for the VIKTOR app.

This module converts the retaining-wall domain model into app-facing result
structures for summary views, tables, and exports.
"""

from ui_app.services.upload_service import load_uploaded_measurements
from ui_app.view_models import (
    BatchAnalysisResult,
    BatchAnalysisResult,
    PileRow,
    WallAnalysisResult,
    WallSummary,
)
from soft_shell_calculator_lib.models.retaining_wall import RetainingWall
from soft_shell_calculator_lib.models.wooden_pile import WoodenPile


def analyze_uploaded_measurements(uploaded_file: object) -> WallAnalysisResult:
    """Analyze an uploaded measurement archive for UI consumption.

    Args:
        uploaded_file: VIKTOR `FileResource`-like object.

    Returns:
        Wall analysis result ready for VIKTOR views and downloads.
    """
    uploaded_measurements = load_uploaded_measurements(uploaded_file)
    pile_rows = _build_pile_rows(uploaded_measurements.retaining_wall)
    failed_pile_count = sum(1 for row in pile_rows if row.error_message is not None)
    warning_pile_count = sum(1 for row in pile_rows if row.warnings)

    summary = WallSummary(
        source_filename=uploaded_measurements.source_filename,
        retaining_wall_id=uploaded_measurements.retaining_wall.id,
        construction_part_count=len(
            uploaded_measurements.retaining_wall.construction_parts
        ),
        pile_count=len(pile_rows),
        measurement_count=sum(row.measurement_count for row in pile_rows),
        valid_file_count=uploaded_measurements.valid_rgp_count,
        skipped_files=uploaded_measurements.skipped_files,
        failed_pile_count=failed_pile_count,
        warning_pile_count=warning_pile_count,
    )

    return WallAnalysisResult(summary=summary, pile_rows=tuple(pile_rows))


def _build_pile_rows(retaining_wall: RetainingWall) -> list[PileRow]:
    """Build flat pile rows from the retaining-wall hierarchy.

    Args:
        retaining_wall: Retaining wall domain object.

    Returns:
        Sorted list of flat pile rows.
    """
    pile_rows: list[PileRow] = []

    for construction_part in retaining_wall.construction_parts:
        for pile in construction_part.wooden_piles:
            pile_rows.append(
                _build_pile_row(
                    retaining_wall_id=retaining_wall.id,
                    construction_part_id=construction_part.id,
                    pile=pile,
                )
            )

    return sorted(pile_rows, key=lambda row: (row.construction_part_id, row.pile_id))


def _build_pile_row(
    retaining_wall_id: str,
    construction_part_id: str,
    pile: WoodenPile,
) -> PileRow:
    """Build one pile row from a pile domain object.

    Args:
        retaining_wall_id: Identifier of the retaining wall.
        construction_part_id: Identifier of the construction part.
        pile: Pile domain object.

    Returns:
        Flat row representation of the pile.
    """
    measurement_ids = tuple(
        measurement.identifier.measurement_id for measurement in pile.rpd_measurements
    )
    high_drill_amplitude = pile.has_high_drill_amplitude

    try:
        diameter_mm = pile.diameter
        annual_rings = pile.number_of_annual_rings
        sapwood_thickness_mm = pile.sapwood_thickness
        heartwood_thickness_mm = pile.heartwood_thickness
        soft_shell_entrance_mm = pile.soft_shell_entrance_thickness
        soft_shell_exit_mm = pile.soft_shell_exit_thickness
        asymmetric_soft_shell = pile.has_asymmetric_soft_shell
    except ValueError as exc:
        warnings = _build_warning_messages(
            high_drill_amplitude=high_drill_amplitude,
            asymmetric_soft_shell=False,
        )
        return PileRow(
            retaining_wall_id=retaining_wall_id,
            construction_part_id=construction_part_id,
            pile_id=pile.id,
            measurement_ids=measurement_ids,
            measurement_count=len(pile.rpd_measurements),
            diameter_mm=None,
            annual_rings=None,
            sapwood_thickness_mm=None,
            heartwood_thickness_mm=None,
            soft_shell_entrance_mm=None,
            soft_shell_exit_mm=None,
            high_drill_amplitude=high_drill_amplitude,
            asymmetric_soft_shell=False,
            warnings=warnings,
            status="Fout",
            error_message=str(exc),
        )

    warnings = _build_warning_messages(
        high_drill_amplitude=high_drill_amplitude,
        asymmetric_soft_shell=asymmetric_soft_shell,
    )
    status = "Waarschuwing" if warnings else "OK"

    return PileRow(
        retaining_wall_id=retaining_wall_id,
        construction_part_id=construction_part_id,
        pile_id=pile.id,
        measurement_ids=measurement_ids,
        measurement_count=len(pile.rpd_measurements),
        diameter_mm=diameter_mm,
        annual_rings=annual_rings,
        sapwood_thickness_mm=sapwood_thickness_mm,
        heartwood_thickness_mm=heartwood_thickness_mm,
        soft_shell_entrance_mm=soft_shell_entrance_mm,
        soft_shell_exit_mm=soft_shell_exit_mm,
        high_drill_amplitude=high_drill_amplitude,
        asymmetric_soft_shell=asymmetric_soft_shell,
        warnings=warnings,
        status=status,
        error_message=None,
    )


def _build_warning_messages(
    high_drill_amplitude: bool,
    asymmetric_soft_shell: bool,
) -> tuple[str, ...]:
    """Return user-facing warnings for a pile.

    Args:
        high_drill_amplitude: Whether high drill amplitude was detected.
        asymmetric_soft_shell: Whether asymmetric soft shell was detected.

    Returns:
        Tuple of warning messages.
    """
    warnings: list[str] = []
    if high_drill_amplitude:
        warnings.append("Hoge booramplitude")
    if asymmetric_soft_shell:
        warnings.append("Asymmetrische zachte schil")
    return tuple(warnings)


_batch_cache: dict[str, BatchAnalysisResult] = {}


def _fingerprint(uploaded_files: list) -> str:
    """Stable cache key derived from uploaded filenames.

    Args:
        uploaded_files: List of VIKTOR FileResource-like objects.

    Returns:
        Sorted, joined filename string used as a cache key.
    """
    names = sorted(getattr(f, "filename", "") for f in uploaded_files)
    return "|".join(names)


def get_batch(uploaded_files: list) -> BatchAnalysisResult:
    """Return cached batch result, computing it on first call per file set.

    Args:
        uploaded_files: List of VIKTOR FileResource-like objects.

    Returns:
        Cached or freshly computed batch result.
    """
    key = _fingerprint(uploaded_files)
    if key not in _batch_cache:
        _batch_cache[key] = analyze_batch_uploaded_measurements(uploaded_files)
    return _batch_cache[key]


def analyze_batch_uploaded_measurements(uploaded_files: list) -> BatchAnalysisResult:
    """Analyze multiple uploaded zip files, one per retaining wall.

    Files that fail analysis are skipped and recorded in ``skipped_walls``.

    Args:
        uploaded_files: List of VIKTOR FileResource-like objects.

    Returns:
        Batch result with per-wall analyses and skipped wall filenames.
    """
    wall_results: list[WallAnalysisResult] = []
    skipped_walls: list[str] = []

    for uploaded_file in uploaded_files:
        source_filename = getattr(uploaded_file, "filename", "onbekend bestand")
        try:
            result = analyze_uploaded_measurements(uploaded_file)
            wall_results.append(result)
        except Exception:
            skipped_walls.append(source_filename)

    return BatchAnalysisResult(
        wall_results=tuple(wall_results),
        skipped_walls=tuple(skipped_walls),
    )
