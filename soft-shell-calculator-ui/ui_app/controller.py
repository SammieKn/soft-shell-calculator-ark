"""Controller definition for the VIKTOR app.

This module should define the output views, download handlers, and the
high-level interaction flow between the parametrization and the services.
The controller should remain thin and delegate real work to the service layer.
"""

import plotly.graph_objects as go
import viktor as vkt

from ui_app.parametrization import Parametrization
from ui_app.services.analysis_service import (
    analyze_batch_uploaded_measurements,
    apply_validation_filter,
)
from ui_app.services.export_service import build_batch_zip
from ui_app.services.plot_service import (
    build_diameter_histogram,
    build_pile_figure,
)
from ui_app.view_models import (
    BatchAnalysisResult,
    PileRow,
    WallAnalysisResult,
)

_TABLE_HEADERS = [
    "Constructiedeel",
    "Paal",
    "Metingen",
    "Diameter [mm]",
    "Jaar-ringen [-]",
    "Spinthout [mm]",
    "Kernhout [mm]",
    "Zachte schil links [mm]",
    "Zachte schil rechts [mm]",
    "Waarschuwingen",
    "Status",
    "Foutmelding",
]
"""Column headers for the pile-level table view (Dutch labels)."""


class Controller(vkt.Controller):
    """Top-level VIKTOR controller for the soft shell calculator."""

    parametrization = Parametrization

    @vkt.DataView("Samenvatting")
    def show_summary(self, params, **kwargs):
        """Show a wall-level summary for the selected retaining wall."""
        batch, wall_result = self._resolve_wall(params)
        if not batch.wall_results and not batch.skipped_walls:
            data = vkt.DataGroup(
                vkt.DataItem("Status", "Upload meetbestanden om de analyse te starten.")
            )
            return vkt.DataResult(data)

        if wall_result is None:
            items = [
                vkt.DataItem("Geanalyseerde kades", len(batch.wall_results)),
                vkt.DataItem(
                    "Status",
                    "Selecteer een kade in het linker paneel om de samenvatting te bekijken.",
                ),
            ]
            if batch.skipped_walls:
                items.append(
                    vkt.DataItem(
                        "Overgeslagen uploads",
                        ", ".join(batch.skipped_walls),
                    )
                )
            return vkt.DataResult(vkt.DataGroup(*items))

        summary = wall_result.summary
        skipped_files = (
            ", ".join(summary.skipped_files) if summary.skipped_files else "Geen"
        )
        items = [
            vkt.DataItem("Bronbestand", summary.source_filename),
            vkt.DataItem("Kade", summary.retaining_wall_id),
            vkt.DataItem("Constructiedelen", summary.construction_part_count),
            vkt.DataItem("Palen", summary.pile_count),
            vkt.DataItem("Metingen", summary.measurement_count),
            vkt.DataItem("Geldige bestanden", summary.valid_file_count),
            vkt.DataItem("Palen met waarschuwing", summary.warning_pile_count),
            vkt.DataItem("Palen met fout", summary.failed_pile_count),
            vkt.DataItem("Overgeslagen bestanden", skipped_files),
        ]
        if batch.skipped_walls:
            items.append(
                vkt.DataItem(
                    "Overgeslagen uploads",
                    ", ".join(batch.skipped_walls),
                )
            )
        return vkt.DataResult(vkt.DataGroup(*items))

    @vkt.TableView("Paaloverzicht")
    def show_pile_table(self, params, **kwargs):
        """Show pile-level results for the selected retaining wall."""
        batch, wall_result = self._resolve_wall(params)

        if not batch.wall_results and not batch.skipped_walls:
            return vkt.TableResult(
                [
                    [
                        "-",
                        "-",
                        "-",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "Upload eerst meetbestanden",
                    ]
                ],
                column_headers=_TABLE_HEADERS,
            )

        if wall_result is None:
            return vkt.TableResult(
                [
                    [
                        "-",
                        "-",
                        "-",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "Selecteer een kade in het linker paneel",
                    ]
                ],
                column_headers=_TABLE_HEADERS,
            )

        def fmt(v: float | None) -> str:
            return f"{v:.1f}" if v is not None else ""

        table_data = [
            [
                row.construction_part_id,
                row.pile_id,
                ", ".join(row.measurement_ids),
                fmt(row.diameter_mm),
                row.annual_rings if row.annual_rings is not None else "",
                fmt(row.sapwood_thickness_mm),
                fmt(row.heartwood_thickness_mm),
                fmt(row.soft_shell_entrance_mm),
                fmt(row.soft_shell_exit_mm),
                "; ".join(row.warnings),
                row.status,
                row.error_message or "",
            ]
            for row in wall_result.pile_rows
        ]
        return vkt.TableResult(table_data, column_headers=_TABLE_HEADERS)

    def download_all(self, params, **kwargs):
        """Return a zip archive with CSV, JSON and HTML pile report for every wall."""
        files = self._get_uploaded_files(params)
        batch = analyze_batch_uploaded_measurements(files)
        batch = apply_validation_filter(batch, self._excluded_piles(params))
        zip_bytes = build_batch_zip(batch)
        return vkt.DownloadResult(
            file_content=zip_bytes,
            file_name="soft_shell_calculator_resultaten.zip",
        )

    @vkt.PlotlyView("Diameterhistogram")
    def show_diameter_histogram(self, params, **kwargs):
        """Show a sorted bar chart of pile diameters for the selected wall."""
        batch, wall_result = self._resolve_wall(params)
        if not batch.wall_results and not batch.skipped_walls:
            return self._empty_plotly("Upload meetbestanden om de grafiek te tonen.")
        if wall_result is None:
            return self._empty_plotly("Selecteer een kade om de grafiek te tonen.")
        return vkt.PlotlyResult(build_diameter_histogram(wall_result))

    @vkt.PlotlyView("Signalen & dwarsdoorsnede")
    def show_pile_overview(self, params, **kwargs):
        """Show drilling resistance and cross-section for the selected pile."""
        batch, wall_result = self._resolve_wall(params)
        if not batch.wall_results and not batch.skipped_walls:
            return self._empty_plotly("Upload meetbestanden om de grafiek te tonen.")
        if wall_result is None:
            return self._empty_plotly("Selecteer een kade om de grafiek te tonen.")
        selected_pile_id = getattr(params.tab_invoer, "geselecteerde_paal", None)
        pile_row = self._find_pile_row(wall_result, selected_pile_id)
        if pile_row is None:
            return self._empty_plotly("Geen paaldata beschikbaar.")
        return vkt.PlotlyResult(build_pile_figure(pile_row))

    def load_validation_table(self, params, **kwargs):
        """Populate the validation table with all piles from the uploaded files.

        All piles are marked as included by default. Existing table content is
        replaced so the table always reflects the current set of uploaded files.

        Args:
            params: VIKTOR params object.

        Returns:
            SetParamsResult that fills ``tab_validatie.palen`` with every pile.
        """
        files = self._get_uploaded_files(params)
        if not files:
            return vkt.SetParamsResult({})
        batch = analyze_batch_uploaded_measurements(files)
        table_rows = [
            {
                "kade": pile_row.retaining_wall_id,
                "constructiedeel": pile_row.construction_part_id,
                "paal": pile_row.pile_id,
                "meting": ", ".join(pile_row.measurement_ids),
                "diameter": pile_row.diameter_mm,
                "opnemen": True,
            }
            for wall_result in batch.wall_results
            for pile_row in wall_result.pile_rows
        ]
        return vkt.SetParamsResult({"tab_validatie": {"palen": table_rows}})

    def _resolve_wall(
        self, params
    ) -> tuple[BatchAnalysisResult, WallAnalysisResult | None]:
        """Load, filter, and find the selected wall in one step.

        Args:
            params: VIKTOR params object.

        Returns:
            Tuple of (batch, wall_result). batch is empty when no files are
            uploaded; wall_result is None when no matching wall exists.
        """
        files = self._get_uploaded_files(params)
        if not files:
            return BatchAnalysisResult(wall_results=(), skipped_walls=()), None
        batch = analyze_batch_uploaded_measurements(files)
        batch = apply_validation_filter(batch, self._excluded_piles(params))
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        return batch, self._find_wall_result(batch, selected_wall_id)

    @staticmethod
    def _empty_plotly(message: str) -> vkt.PlotlyResult:
        """Return a PlotlyResult with a single centred annotation.

        Args:
            message: Text to display in the empty figure.

        Returns:
            PlotlyResult containing an annotation-only figure.
        """
        fig = go.Figure()
        fig.add_annotation(text=message, showarrow=False)
        return vkt.PlotlyResult(fig)

    @staticmethod
    def _excluded_piles(params) -> set[tuple[str, str]]:
        """Extract (wall_id, pile_id) pairs marked for exclusion.

        Args:
            params: VIKTOR params object.

        Returns:
            Set of (retaining_wall_id, pile_id) tuples for unchecked piles.
        """
        rows = getattr(getattr(params, "tab_validatie", None), "palen", None) or []
        return {
            (getattr(r, "kade", ""), getattr(r, "paal", ""))
            for r in rows
            if not getattr(r, "opnemen", True)
        }

    @staticmethod
    def _get_uploaded_files(params) -> list:
        """Return the list of uploaded files from the parametrization.

        Args:
            params: VIKTOR params object.

        Returns:
            List of uploaded file resources, empty if none uploaded.
        """
        return getattr(params.tab_invoer, "meetbestanden", None) or []

    @staticmethod
    def _find_wall_result(
        batch: BatchAnalysisResult, selected_wall_id: str | None
    ) -> WallAnalysisResult | None:
        """Find the wall result matching the selected wall ID.

        Falls back to the first alphabetical wall when no selection is made,
        so results are shown immediately after upload without user interaction.

        Args:
            batch: Batch analysis result containing all wall results.
            selected_wall_id: The retaining-wall ID chosen by the user.

        Returns:
            Matching wall result, first alphabetical wall as fallback, or
            ``None`` if the batch contains no results.
        """
        if not batch.wall_results:
            return None
        if selected_wall_id:
            for result in batch.wall_results:
                if result.summary.retaining_wall_id == selected_wall_id:
                    return result
        # No selection or stale selection — return first alphabetical wall
        return min(batch.wall_results, key=lambda r: r.summary.retaining_wall_id)

    @staticmethod
    def _find_pile_row(
        wall_result: WallAnalysisResult, selected_pile_id: str | None
    ) -> PileRow | None:
        """Find the pile row matching the selected pile ID.

        Falls back to the first alphabetical pile when no selection is made.

        Args:
            wall_result: Wall analysis result containing pile rows.
            selected_pile_id: The pile ID chosen by the user.

        Returns:
            Matching pile row, first alphabetical pile as fallback, or
            ``None`` if the wall has no pile rows.
        """
        if not wall_result.pile_rows:
            return None
        if selected_pile_id:
            for row in wall_result.pile_rows:
                if row.pile_id == selected_pile_id:
                    return row
        return min(wall_result.pile_rows, key=lambda r: r.pile_id)
