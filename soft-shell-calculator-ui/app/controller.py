"""Controller definition for the VIKTOR app.

This module should define the output views, download handlers, and the
high-level interaction flow between the parametrization and the application
services. The controller should remain thin and delegate real work to the
service layer.
"""

import viktor as vkt

from app.parametrization import Parametrization


class Controller(vkt.Controller):
    """Top-level VIKTOR controller for the soft shell calculator."""

    parametrization = Parametrization

    @vkt.DataView("Samenvatting")
    def show_summary(self, params, **kwargs):
        """Show a temporary scaffold summary until the app is implemented."""
        data = vkt.DataGroup(
            vkt.DataItem(
                "Status",
                "App-structuur aangemaakt",
                explanation_label="De functionele implementatie volgt in volgende stappen.",
            )
        )
        return vkt.DataResult(data)
