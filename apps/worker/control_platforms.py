"""
Per-platform control helpers (Patch 25.1).

Adds lightweight state files for:
- per-platform status badges
- per-run platform selection override
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional


PLATFORM_STATE_DIR = Path("data/.control/platforms")
SESSION_OVERRIDE_FILE = Path("data/.control/session_override.json")
PREFERRED_SELECTION_FILE = Path("data/.control/preferred_platforms.json")


def init_platform_state():
    """Ensure platform control directories exist."""
    PLATFORM_STATE_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_OVERRIDE_FILE.parent.mkdir(parents=True, exist_ok=True)


def set_platform_state(platform: str, state: str, extra: dict | None = None):
    """Persist state for a single platform."""
    init_platform_state()
    data = {
        "platform": platform,
        "state": state,
        "updated_at": int(time.time()),
    }
    if extra:
        data.update(extra)
    (PLATFORM_STATE_DIR / f"{platform}.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def get_platform_state(platform: str) -> dict:
    """Return current state for one platform."""
    state_file = PLATFORM_STATE_DIR / f"{platform}.json"
    if not state_file.exists():
        return {"platform": platform, "state": "idle"}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {"platform": platform, "state": "unknown"}


def get_all_platform_states() -> dict:
    """Return all tracked platform states."""
    init_platform_state()
    states = {}
    for state_file in PLATFORM_STATE_DIR.glob("*.json"):
        platform = state_file.stem
        try:
            states[platform] = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            states[platform] = {"platform": platform, "state": "unknown"}
    return states


def clear_platform_states():
    """Delete all stored platform state files."""
    init_platform_state()
    for state_file in PLATFORM_STATE_DIR.glob("*.json"):
        state_file.unlink()


def set_session_platforms(platforms: list[str], mode: str = "sequential"):
    """Store one-run platform selection override."""
    init_platform_state()
    SESSION_OVERRIDE_FILE.write_text(
        json.dumps(
            {
                "platforms": platforms,
                "mode": mode,
                "created_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def get_session_platforms() -> Optional[dict]:
    """Read current session override, if present."""
    if not SESSION_OVERRIDE_FILE.exists():
        return None
    try:
        return json.loads(SESSION_OVERRIDE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_session_override():
    """Remove session override after run ends."""
    if SESSION_OVERRIDE_FILE.exists():
        SESSION_OVERRIDE_FILE.unlink()


def set_preferred_platforms(platforms: list[str], mode: str = "sequential"):
    """Persist the preferred platform selection for future Start actions."""
    init_platform_state()
    PREFERRED_SELECTION_FILE.write_text(
        json.dumps(
            {
                "platforms": platforms,
                "mode": mode,
                "updated_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def get_preferred_platforms() -> Optional[dict]:
    """Read preferred platform selection, if present."""
    if not PREFERRED_SELECTION_FILE.exists():
        return None
    try:
        return json.loads(PREFERRED_SELECTION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_preferred_platforms():
    """Remove saved preferred selection."""
    if PREFERRED_SELECTION_FILE.exists():
        PREFERRED_SELECTION_FILE.unlink()
