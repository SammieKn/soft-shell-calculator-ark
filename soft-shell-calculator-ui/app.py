"""Thin VIKTOR entrypoint for the soft shell calculator app.

This module should stay minimal and expose the public Parametrization and
Controller classes from the dedicated app package. All VIKTOR-specific
implementation details should live under the app package.
"""

from ui_app.controller import Controller
from ui_app.parametrization import Parametrization
