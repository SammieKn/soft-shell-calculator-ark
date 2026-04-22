"""Parametrization definition for the VIKTOR app.

This module should define the full left-panel input structure for the app,
including uploads, selection fields, advanced options, and download buttons.
User-facing labels and help text should be kept in Dutch.
"""

import viktor as vkt


class Parametrization(vkt.Parametrization):
    """Top-level VIKTOR parametrization for the soft shell calculator."""

    tab_invoer = vkt.Tab("Invoer")
    tab_invoer.uitleg = vkt.Text(
        "Upload een zip-bestand met .rgp-metingen of een enkel .rgp-bestand. "
        "De eerste versie toont een samenvatting, een paaloverzicht en een csv-download."
    )
    tab_invoer.meetbestand = vkt.FileField(
        "Meetbestand",
        file_types=[".zip", ".rgp"],
        description="Ondersteunt een zip met .rgp-metingen of een enkel .rgp-bestand.",
    )

    tab_analyse = vkt.Tab("Analyse")
    tab_analyse.status = vkt.Text(
        "De analyse draait automatisch zodra een geldig meetbestand is geupload."
    )

    tab_resultaten = vkt.Tab("Resultaten")
    tab_resultaten.download_csv = vkt.DownloadButton(
        "Download csv",
        method="download_csv",
        longpoll=True,
    )
    tab_resultaten.status = vkt.Text(
        "Gebruik de uitvoerviews rechts om de samenvatting en het paaloverzicht te bekijken."
    )
