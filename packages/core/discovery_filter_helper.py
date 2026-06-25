"""
Discovery Mode Filter Helper (Patch 33.2).

Helper to bypass strict filters when bot is in discovery mode.
Discovery philosophy: scrape broad, let user filter in UI.
"""
from typing import Any


def should_apply_filter(filter_type: str, discovery_mode: bool, queue_item: Any = None) -> bool:
    """
    Decide if a filter should be applied based on mode.

    Returns True if the filter should be enforced for the current item.
    """
    if queue_item:
        return False

    if discovery_mode:
        critical_filters = {"already_applied", "rate_limit"}
        return filter_type in critical_filters

    return True
