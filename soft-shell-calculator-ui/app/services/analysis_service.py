"""Analysis orchestration service for the VIKTOR app.

This module should coordinate the calculation library and convert domain
objects into app-level result structures for pile-level and construction-part
level reporting.
"""

from app.view_models import SummaryCard


def build_placeholder_summary() -> list[SummaryCard]:
    """Return a placeholder summary model for the scaffolded app.

    Returns:
        List with one temporary summary card.
    """
    return [SummaryCard(label="Status", value="Nog niet geimplementeerd")]
