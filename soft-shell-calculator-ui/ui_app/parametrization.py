"""Parametrization definition for the VIKTOR app.

This module should define the full left-panel input structure for the app,
including uploads, selection fields, advanced options, and download buttons.
User-facing labels and help text should be kept in Dutch.
"""

import viktor as vkt

from ui_app.services.upload_service import peek_wall_id_from_file_resource


def _get_wall_options(params, **kwargs) -> list[str]:
    """Return the list of retaining-wall IDs available for selection.

    Args:
        params: VIKTOR params object.

    Returns:
        List of wall IDs derived from the uploaded zip filenames.
    """
    files = getattr(getattr(params, "tab_invoer", None), "meetbestanden", None) or []
    options: list[str] = []
    for uploaded_file in files:
        wall_id = peek_wall_id_from_file_resource(uploaded_file)
        if wall_id and wall_id not in options:
            options.append(wall_id)
    return sorted(options)


def _natural_sort_key(pile_id: str) -> tuple:
    import re

    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", pile_id)
    )


def _get_pile_options(params, **kwargs) -> list[str]:
    """Return pile IDs for the selected wall.

    Args:
        params: VIKTOR params object.

    Returns:
        Naturally sorted list of pile IDs for the currently selected wall.
    """
    from ui_app.services.analysis_service import get_batch

    files = getattr(getattr(params, "tab_invoer", None), "meetbestanden", None) or []
    if not files:
        return []
    selected_wall_id = getattr(params.tab_invoer, "geselecteerde_kade", None)
    batch = get_batch(files)
    for wall_result in batch.wall_results:
        if wall_result.summary.retaining_wall_id == selected_wall_id:
            return sorted(
                (row.pile_id for row in wall_result.pile_rows), key=_natural_sort_key
            )
    if batch.wall_results:
        first = min(batch.wall_results, key=lambda r: r.summary.retaining_wall_id)
        return sorted((row.pile_id for row in first.pile_rows), key=_natural_sort_key)
    return []


class Parametrization(vkt.Parametrization):
    """Top-level VIKTOR parametrization for the soft shell calculator."""

    tab_invoer = vkt.Tab("Invoer")
    tab_invoer.uitleg = vkt.Text(
        "Upload één of meerdere zip-bestanden met .rgp-metingen. "
        "Elk zip-bestand vertegenwoordigt één kade. "
        "Na het uploaden kunt u een kade selecteren om de resultaten te bekijken."
    )
    tab_invoer.meetbestanden = vkt.MultiFileField(
        "Meetbestanden",
        file_types=[".zip"],
        description="Upload één of meerdere zip-bestanden. Elk zip-bestand vertegenwoordigt één kade.",
    )
    tab_invoer.geselecteerde_kade = vkt.OptionField(
        "Geselecteerde kade",
        options=_get_wall_options,
        description="Selecteer een kade om de bijbehorende resultaten te bekijken.",
        autoselect_single_option=True,
    )
    tab_invoer.geselecteerde_paal = vkt.OptionField(
        "Geselecteerde paal",
        options=_get_pile_options,
        description="Selecteer een paal om het signaal en de dwarsdoorsnede te bekijken.",
        autoselect_single_option=True,
    )

    tab_resultaten = vkt.Tab("Resultaten")
    tab_resultaten.download_all = vkt.DownloadButton(
        "Download alles (csv + json + paalrapport, alle kades)",
        method="download_all",
        longpoll=True,
    )
    tab_resultaten.status = vkt.Text(
        "Gebruik de uitvoerviews rechts om de samenvatting en het paaloverzicht te bekijken."
    )
