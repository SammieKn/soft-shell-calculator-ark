"""Parametrization definition for the VIKTOR app.

This module should define the full left-panel input structure for the app,
including uploads, selection fields, advanced options, and download buttons.
User-facing labels and help text should be kept in Dutch.
"""

import viktor as vkt

from ui_app.services.upload_service import peek_wall_ids_from_file_resource
from ui_app.services.upload_service import peek_pile_ids_from_file_resource
from ui_app.services.upload_service import _natural_sort_key


def _get_wall_options(params, **kwargs) -> list[str]:
    """Return the list of retaining-wall IDs available for selection.

    Args:
        params: VIKTOR params object.

    Returns:
        Sorted list of wall IDs derived from the uploaded zip filenames.
    """
    files = getattr(getattr(params, "tab_invoer", None), "meetbestanden", None) or []
    options: list[str] = []
    for uploaded_file in files:
        for wall_id in peek_wall_ids_from_file_resource(uploaded_file):
            if wall_id not in options:
                options.append(wall_id)
    return sorted(options)


def _get_pile_options(params, **kwargs) -> list[str]:
    """Return pile IDs for the selected wall by reading zip filenames only.

    Derives pile IDs directly from `.rgp` filename stems in the uploaded zip —
    no analysis is performed, keeping the parametrization render fast.

    Args:
        params: VIKTOR params object.

    Returns:
        Naturally sorted list of pile IDs for the currently selected wall.
    """
    files = getattr(getattr(params, "tab_invoer", None), "meetbestanden", None) or []
    if not files:
        return []
    selected_wall_id = getattr(
        getattr(params, "tab_invoer", None), "geselecteerde_kade", None
    )
    pile_ids: list[str] = []
    for uploaded_file in files:
        wall_ids_in_file = peek_wall_ids_from_file_resource(uploaded_file)
        if selected_wall_id and selected_wall_id not in wall_ids_in_file:
            continue
        for pid in peek_pile_ids_from_file_resource(uploaded_file, selected_wall_id):
            if pid not in pile_ids:
                pile_ids.append(pid)
    return sorted(pile_ids, key=_natural_sort_key)


class Parametrization(vkt.Parametrization):
    """Top-level VIKTOR parametrization for the soft shell calculator."""

    tab_invoer = vkt.Tab("Invoer")
    tab_invoer.uitleg = vkt.Text(
        "Upload één of meerdere zip-bestanden met .rgp-metingen. "
        "Een zip-bestand mag metingen van meerdere kades bevatten. "
        "Na het uploaden kunt u een kade selecteren om de resultaten te bekijken."
    )
    tab_invoer.meetbestanden = vkt.MultiFileField(
        "Meetbestanden",
        file_types=[".zip"],
        description="Upload één of meerdere zip-bestanden met .rgp-metingen.",
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

    tab_validatie = vkt.Tab("Validatie")
    tab_validatie.uitleg = vkt.Text(
        "Gebruik deze tab om palen uit te sluiten van de analyse en export. "
        "Klik op 'Laad palen' om de tabel te vullen met alle palen uit de geüploade bestanden. "
        "Verwijder het vinkje bij 'Opnemen' om een paal uit te sluiten."
    )
    tab_validatie.laad_palen = vkt.SetParamsButton(
        "Laad palen",
        method="load_validation_table",
    )
    tab_validatie.palen = vkt.Table("Palen")
    tab_validatie.palen.kade = vkt.TextField("Kade")
    tab_validatie.palen.constructiedeel = vkt.TextField("Constructiedeel")
    tab_validatie.palen.paal = vkt.TextField("Paal")
    tab_validatie.palen.meting = vkt.TextField("Meting")
    tab_validatie.palen.diameter = vkt.NumberField("Diameter [mm]")
    tab_validatie.palen.opnemen = vkt.BooleanField("Opnemen")

    tab_resultaten = vkt.Tab("Resultaten")
    tab_resultaten.download_all = vkt.DownloadButton(
        "Download alles (csv + json + paalrapport, alle kades)",
        method="download_all",
        longpoll=True,
    )
    tab_resultaten.status = vkt.Text(
        "Gebruik de uitvoerviews rechts om de samenvatting en het paaloverzicht te bekijken."
    )
