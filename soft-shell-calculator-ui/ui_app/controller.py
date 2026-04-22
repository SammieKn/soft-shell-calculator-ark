"""Controller definition for the VIKTOR app.

This module should define the output views, download handlers, and the
high-level interaction flow between the parametrization and the application
services. The controller should remain thin and delegate real work to the
service layer.
"""

import viktor as vkt

from ui_app.parametrization import Parametrization
from ui_app.services.analysis_service import analyze_uploaded_measurements
from ui_app.services.export_service import build_pile_csv


class Controller(vkt.Controller):
    """Top-level VIKTOR controller for the soft shell calculator."""

    parametrization = Parametrization

    @vkt.DataView("Samenvatting")
    def show_summary(self, params, **kwargs):
        """Show a wall-level summary for the uploaded measurements."""
        uploaded_file = self._get_uploaded_file(params)
        if uploaded_file is None:
            data = vkt.DataGroup(
                vkt.DataItem(
                    "Status",
                    "Upload een meetbestand om de analyse te starten.",
                )
            )
            return vkt.DataResult(data)

        try:
            analysis_result = analyze_uploaded_measurements(uploaded_file)
        except ValueError as exc:
            data = vkt.DataGroup(
                vkt.DataItem("Status", "Analyse mislukt"),
                vkt.DataItem("Melding", str(exc)),
            )
            return vkt.DataResult(data)

        skipped_files = ", ".join(analysis_result.summary.skipped_files)
        data = vkt.DataGroup(
            vkt.DataItem("Bronbestand", analysis_result.summary.source_filename),
            vkt.DataItem("Kade", analysis_result.summary.retaining_wall_id),
            vkt.DataItem(
                "Constructiedelen",
                analysis_result.summary.construction_part_count,
            ),
            vkt.DataItem("Palen", analysis_result.summary.pile_count),
            vkt.DataItem("Metingen", analysis_result.summary.measurement_count),
            vkt.DataItem(
                "Geldige bestanden",
                analysis_result.summary.valid_file_count,
            ),
            vkt.DataItem(
                "Palen met waarschuwing",
                analysis_result.summary.warning_pile_count,
            ),
            vkt.DataItem(
                "Palen met fout",
                analysis_result.summary.failed_pile_count,
            ),
            vkt.DataItem(
                "Overgeslagen bestanden",
                skipped_files if skipped_files else "Geen",
            ),
        )
        return vkt.DataResult(data)

    @vkt.TableView("Paaloverzicht")
    def show_pile_table(self, params, **kwargs):
        """Show pile-level results in a tabular overview."""
        uploaded_file = self._get_uploaded_file(params)
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
        if uploaded_file is None:
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
                        "Upload eerst een meetbestand",
                    ]
                ],
                column_headers=column_headers,
            )

        try:
            analysis_result = analyze_uploaded_measurements(uploaded_file)
        except ValueError as exc:
            return vkt.TableResult(
                [["-", "-", "-", "", "", "", "", "", "", "", "Fout", str(exc)]],
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
            for row in analysis_result.pile_rows
        ]
        return vkt.TableResult(table_data, column_headers=column_headers)

    def download_csv(self, params, **kwargs):
        """Return a CSV download for the current pile-level analysis."""
        analysis_result = analyze_uploaded_measurements(self._get_uploaded_file(params))
        csv_bytes = build_pile_csv(analysis_result)
        return vkt.DownloadResult(
            file_content=csv_bytes,
            file_name="soft_shell_calculator_results.csv",
        )

    @staticmethod
    def _get_uploaded_file(params):
        """Return the uploaded file from the parametrization.

        Args:
            params: VIKTOR params object.

        Returns:
            Uploaded file resource or `None`.
        """
        return getattr(params.tab_invoer, "meetbestand", None)

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
