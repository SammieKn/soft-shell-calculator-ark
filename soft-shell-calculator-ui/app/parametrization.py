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
        "Upload een zip-bestand met .rgp-metingen. "
        "De analyse-inhoud wordt in volgende iteraties ingevuld."
    )

    tab_analyse = vkt.Tab("Analyse")
    tab_analyse.status = vkt.Text(
        "Hier komen later analyse-instellingen en procesacties."
    )

    tab_resultaten = vkt.Tab("Resultaten")
    tab_resultaten.status = vkt.Text(
        "Hier komen later selecties, downloads en resultaatfilters."
    )
