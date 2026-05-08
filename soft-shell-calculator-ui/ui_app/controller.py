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
from ui_app.view_models import BatchAnalysisResult, PileRow, WallAnalysisResult


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
        zip_bytes = build_batch_zip(batch)
        return vkt.DownloadResult(
            file_content=zip_bytes,
            file_name="soft_shell_calculator_resultaten.zip",
        )

    def download_all(self, params, **kwargs):
        """Return a zip archive with CSV, JSON and HTML pile report for every wall."""
        files = self._get_uploaded_files(params)
        batch = get_batch(files)
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
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        wall_result = self._find_wall_result(batch, selected_wall_id)
        if wall_result is None:
            fig = go.Figure()
            fig.add_annotation(
                text="Selecteer een kade om de grafiek te tonen.", showarrow=False
            )
            return vkt.PlotlyResult(fig)
        return vkt.PlotlyResult(build_diameter_histogram(wall_result))

    @vkt.DataView("Paal-KPIs")
    def show_pile_kpis(self, params, **kwargs):
        """Show key performance indicators for the selected pile, including Gezonde doorsnede."""
        files = self._get_uploaded_files(params)
        if not files:
            data = vkt.DataGroup(
                vkt.DataItem("Status", "Upload meetbestanden om de KPIs te tonen.")
            )
            return vkt.DataResult(data)
        batch = get_batch(files)
        selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
        wall_result = self._find_wall_result(batch, selected_wall_id)
        if wall_result is None:
            data = vkt.DataGroup(
                vkt.DataItem("Status", "Selecteer een kade om de KPIs te tonen.")
            )
            return vkt.DataResult(data)
        selected_pile_id = getattr(params.tab_invoer, "geselecteerde_paal", None)
        pile_row = self._find_pile_row(wall_result, selected_pile_id)
        if pile_row is None:
            data = vkt.DataGroup(vkt.DataItem("Status", "Geen paaldata beschikbaar."))
            return vkt.DataResult(data)

        items: list[vkt.DataItem] = [
            vkt.DataItem("Paal", pile_row.pile_id),
        ]
        if pile_row.diameter_mm is not None:
            items.append(vkt.DataItem("Diameter", pile_row.diameter_mm, suffix="mm", number_of_decimals=0))
        if pile_row.heartwood_thickness_mm is not None:
            items.append(vkt.DataItem("Kernhout", pile_row.heartwood_thickness_mm, suffix="mm", number_of_decimals=0))
        if pile_row.sapwood_thickness_mm is not None:
            items.append(vkt.DataItem("Spinthout", pile_row.sapwood_thickness_mm, suffix="mm", number_of_decimals=0))
        if pile_row.soft_shell_entrance_mm is not None:
            items.append(vkt.DataItem("Zachte schil links", pile_row.soft_shell_entrance_mm, suffix="mm", number_of_decimals=0))
        if pile_row.soft_shell_exit_mm is not None:
            items.append(vkt.DataItem("Zachte schil rechts", pile_row.soft_shell_exit_mm, suffix="mm", number_of_decimals=0))
        if (
            pile_row.diameter_mm is not None
            and pile_row.soft_shell_entrance_mm is not None
            and pile_row.soft_shell_exit_mm is not None
        ):
            sound_section_mm = pile_row.diameter_mm - pile_row.soft_shell_entrance_mm - pile_row.soft_shell_exit_mm
            items.append(vkt.DataItem("Gezonde doorsnede", sound_section_mm, suffix="mm", number_of_decimals=0))

        return vkt.DataResult(vkt.DataGroup(*items))

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
