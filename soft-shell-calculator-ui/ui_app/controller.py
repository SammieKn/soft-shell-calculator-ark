"""Controller definition for the VIKTOR app.

This module should define the output views, download handlers, and the
high-level interaction flow between the parametrization and the services.
The controller should remain thin and delegate real work to the service layer.
"""

import plotly.graph_objects as go
import viktor as vkt

from ui_app.parametrization import Parametrization
from ui_app.services.analysis_service import get_batch
from ui_app.services.export_service import build_batch_zip
from ui_app.services.plot_service import (
    build_diameter_histogram,
    build_pile_figure,
)
from ui_app.view_models import (
    BatchAnalysisResult,
    PileRow,
    WallAnalysisResult,
    WallSummary,
)


class Controller(vkt.Controller):
    """Top-level VIKTOR controller for the soft shell calculator."""

    parametrization = Parametrization

    @vkt.DataView("Samenvatting")
    def show_summary(self, params, **kwargs):
        """Show a wall-level summary for the selected retaining wall."""
        files = self._get_uploaded_files(params)
        if not files:
            data = vkt.DataGroup(
                vkt.DataItem("Status", "Upload meetbestanden om de analyse te starten.")
            )
            return vkt.DataResult(data)

        batch = get_batch(files)
        batch = self._apply_validation_filter(batch, params)
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        wall_result = self._find_wall_result(batch, selected_wall_id)

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
        column_headers = [
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

        files = self._get_uploaded_files(params)
        if not files:
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
                column_headers=column_headers,
            )

        batch = get_batch(files)
        batch = self._apply_validation_filter(batch, params)
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        wall_result = self._find_wall_result(batch, selected_wall_id)

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
                column_headers=column_headers,
            )

        table_data = [
            [
                row.construction_part_id,
                row.pile_id,
                ", ".join(row.measurement_ids),
                self._format_optional_number(row.diameter_mm),
                row.annual_rings if row.annual_rings is not None else "",
                self._format_optional_number(row.sapwood_thickness_mm),
                self._format_optional_number(row.heartwood_thickness_mm),
                self._format_optional_number(row.soft_shell_entrance_mm),
                self._format_optional_number(row.soft_shell_exit_mm),
                "; ".join(row.warnings),
                row.status,
                row.error_message or "",
            ]
            for row in wall_result.pile_rows
        ]
        return vkt.TableResult(table_data, column_headers=column_headers)

    def download_csv(self, params, **kwargs):
        """Return a zip archive containing one CSV per retaining wall."""
        files = self._get_uploaded_files(params)
        batch = get_batch(files)
        batch = self._apply_validation_filter(batch, params)
        zip_bytes = build_batch_zip(batch)
        return vkt.DownloadResult(
            file_content=zip_bytes,
            file_name="soft_shell_calculator_resultaten.zip",
        )

    def download_all(self, params, **kwargs):
        """Return a zip archive with CSV, JSON and HTML pile report for every wall."""
        files = self._get_uploaded_files(params)
        batch = get_batch(files)
        batch = self._apply_validation_filter(batch, params)
        zip_bytes = build_batch_zip(batch)
        return vkt.DownloadResult(
            file_content=zip_bytes,
            file_name="soft_shell_calculator_resultaten.zip",
        )

    @vkt.PlotlyView("Diameterhistogram")
    def show_diameter_histogram(self, params, **kwargs):
        """Show a sorted bar chart of pile diameters for the selected wall."""
        files = self._get_uploaded_files(params)
        if not files:
            fig = go.Figure()
            fig.add_annotation(
                text="Upload meetbestanden om de grafiek te tonen.", showarrow=False
            )
            return vkt.PlotlyResult(fig)
        batch = get_batch(files)
        batch = self._apply_validation_filter(batch, params)
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        wall_result = self._find_wall_result(batch, selected_wall_id)
        if wall_result is None:
            fig = go.Figure()
            fig.add_annotation(
                text="Selecteer een kade om de grafiek te tonen.", showarrow=False
            )
            return vkt.PlotlyResult(fig)
        return vkt.PlotlyResult(build_diameter_histogram(wall_result))

    @vkt.PlotlyView("Signalen & dwarsdoorsnede")
    def show_pile_overview(self, params, **kwargs):
        """Show drilling resistance and cross-section for the selected pile."""
        files = self._get_uploaded_files(params)
        if not files:
            fig = go.Figure()
            fig.add_annotation(
                text="Upload meetbestanden om de grafiek te tonen.", showarrow=False
            )
            return vkt.PlotlyResult(fig)
        batch = get_batch(files)
        batch = self._apply_validation_filter(batch, params)
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        wall_result = self._find_wall_result(batch, selected_wall_id)
        if wall_result is None:
            fig = go.Figure()
            fig.add_annotation(
                text="Selecteer een kade om de grafiek te tonen.", showarrow=False
            )
            return vkt.PlotlyResult(fig)
        selected_pile_id = getattr(params.tab_invoer, "geselecteerde_paal", None)
        pile_row = self._find_pile_row(wall_result, selected_pile_id)
        if pile_row is None:
            fig = go.Figure()
            fig.add_annotation(text="Geen paaldata beschikbaar.", showarrow=False)
            return vkt.PlotlyResult(fig)
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
        batch = get_batch(files)
        table_rows = [
            {
                "kade": pile_row.retaining_wall_id,
                "constructiedeel": pile_row.construction_part_id,
                "paal": pile_row.pile_id,
                "opnemen": True,
            }
            for wall_result in batch.wall_results
            for pile_row in wall_result.pile_rows
        ]
        return vkt.SetParamsResult({"tab_validatie": {"palen": table_rows}})

    @staticmethod
    def _apply_validation_filter(
        batch: BatchAnalysisResult, params
    ) -> BatchAnalysisResult:
        """Return a filtered batch with unchecked piles removed.

        Reads ``tab_validatie.palen`` from ``params`` and excludes every pile
        whose *Opnemen* checkbox is unchecked. When the table is empty (e.g.
        the user has not yet loaded it) the original batch is returned unchanged.

        Args:
            batch: Full batch analysis result.
            params: VIKTOR params object that may contain a validation table.

        Returns:
            Filtered batch, or the original batch if no exclusions were set.
        """
        validation_rows = (
            getattr(getattr(params, "tab_validatie", None), "palen", None) or []
        )
        if not validation_rows:
            return batch

        excluded: set[tuple[str, str]] = set()
        for row in validation_rows:
            if not getattr(row, "opnemen", True):
                excluded.add(
                    (getattr(row, "kade", ""), getattr(row, "paal", ""))
                )

        if not excluded:
            return batch

        new_wall_results: list[WallAnalysisResult] = []
        for wall_result in batch.wall_results:
            new_pile_rows = tuple(
                pile_row
                for pile_row in wall_result.pile_rows
                if (pile_row.retaining_wall_id, pile_row.pile_id) not in excluded
            )
            new_summary = WallSummary(
                source_filename=wall_result.summary.source_filename,
                retaining_wall_id=wall_result.summary.retaining_wall_id,
                construction_part_count=wall_result.summary.construction_part_count,
                pile_count=len(new_pile_rows),
                measurement_count=sum(r.measurement_count for r in new_pile_rows),
                valid_file_count=wall_result.summary.valid_file_count,
                skipped_files=wall_result.summary.skipped_files,
                failed_pile_count=sum(
                    1 for r in new_pile_rows if r.error_message is not None
                ),
                warning_pile_count=sum(1 for r in new_pile_rows if r.warnings),
            )
            new_wall_results.append(
                WallAnalysisResult(summary=new_summary, pile_rows=new_pile_rows)
            )

        return BatchAnalysisResult(
            wall_results=tuple(new_wall_results),
            skipped_walls=batch.skipped_walls,
        )

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
    def _format_optional_number(value: float | None) -> str:
        """Format an optional number for table output.

        Args:
            value: Optional numeric value.

        Returns:
            Rounded string or an empty string.
        """
        if value is None:
            return ""
        return f"{value:.1f}"

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
