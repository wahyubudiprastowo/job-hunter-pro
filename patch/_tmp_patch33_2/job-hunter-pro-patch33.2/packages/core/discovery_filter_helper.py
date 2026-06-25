"""
Discovery Mode Filter Helper (Patch 33.2).

Helper to bypass strict filters when bot is in discovery mode.
Discovery philosophy: scrape EVERYTHING, let user filter in UI.
"""
from typing import Optional


def should_apply_filter(filter_type: str, discovery_mode: bool, queue_item=None) -> bool:
    """
    Decide if a filter should be applied based on mode.
    
    Args:
        filter_type: "title_keywords", "salary", "company_blacklist", etc.
        discovery_mode: True if bot is in discovery mode
        queue_item: Apply queue item (skip discovery filter if from queue)
    
    Returns: True if filter SHOULD be applied (rejected = continue)
    """
    # Apply queue items: always apply filters (user already curated)
    if queue_item:
        return False  # Don't double-filter user-curated jobs
    
    # Discovery mode: relaxed filtering
    if discovery_mode:
        # Only critical filters apply in discovery
        critical_filters = ["already_applied", "rate_limit"]
        return filter_type in critical_filters
    
    # Apply mode (normal): all filters apply
    return True