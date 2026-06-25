"""
Discovery Trigger Helper (Patch 32.2).

Provides:
1. Session-only config override (no file modification)
2. Platform selection for discovery scrape
3. Status tracking
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Optional

from loguru import logger


DISCOVERY_SESSION_FILE = Path("data/.control/discovery_session.json")


def set_discovery_session(
    platforms: list[str],
    max_per_session: int = 100,
    scroll_depth: int = 15,
) -> bool:
    """Set one-run discovery overrides without touching config.yaml."""
    try:
        DISCOVERY_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        DISCOVERY_SESSION_FILE.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "platforms": platforms,
                    "max_per_session": int(max_per_session),
                    "scroll_depth": int(scroll_depth),
                    "started_at": int(time.time()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(f"Discovery session set: {platforms}, cap={max_per_session}")
        return True
    except Exception as e:
        logger.error(f"Set discovery session failed: {e}")
        return False


def get_discovery_session() -> Optional[dict]:
    """Read current discovery session override, if any."""
    try:
        if not DISCOVERY_SESSION_FILE.exists():
            return None
        return json.loads(DISCOVERY_SESSION_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug(f"Read discovery session failed: {e}")
        return None


def clear_discovery_session():
    """Remove discovery session override after run."""
    try:
        if DISCOVERY_SESSION_FILE.exists():
            DISCOVERY_SESSION_FILE.unlink()
            logger.debug("Discovery session cleared")
    except Exception as e:
        logger.debug(f"Clear discovery session failed: {e}")


def merge_discovery_config(config: dict) -> dict:
    """Merge session discovery override into loaded config."""
    session = get_discovery_session()
    if not session:
        return config

    cfg = copy.deepcopy(config)
    discovery_cfg = cfg.setdefault("discovery", {})
    discovery_cfg["enabled"] = True
    if "max_per_session" in session:
        discovery_cfg["max_per_session"] = session["max_per_session"]
    if "scroll_depth" in session:
        discovery_cfg["scroll_depth"] = session["scroll_depth"]
    return cfg
