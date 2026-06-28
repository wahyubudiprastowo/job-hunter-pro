"""
Chrome profile management helpers for the web settings UI.

Keeps the implementation additive and aligned with the profile resolution
already used by the worker.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


PROFILE_REGISTRY = Path("data/.control/profile_registry.json")


def find_chrome_binary() -> Optional[str]:
    chrome_env = (os.getenv("CHROME_BINARY") or "").strip()
    if chrome_env and Path(chrome_env).exists():
        return chrome_env

    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _resolve_glassdoor_target_url() -> str:
    region = (os.getenv("GLASSDOOR_REGION") or "").strip().lower()
    if not region:
        try:
            cfg_path = Path("config.yaml")
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            gd_cfg = ((cfg.get("platforms") or {}).get("glassdoor") or {})
            region = str(gd_cfg.get("region") or "").strip().lower()
            if region in ("", "auto"):
                location = str(((gd_cfg.get("search") or {}).get("location") or "")).lower()
                if "singapore" in location:
                    region = "sg"
                elif "germany" in location or "berlin" in location or "munich" in location:
                    region = "de"
                elif "france" in location or "paris" in location:
                    region = "fr"
                elif "netherlands" in location or "amsterdam" in location:
                    region = "nl"
                elif "ireland" in location or "dublin" in location:
                    region = "ie"
                else:
                    region = ""
        except Exception:
            region = ""

    region_map = {
        "us": "https://www.glassdoor.com/",
        "uk": "https://www.glassdoor.co.uk/",
        "ca": "https://www.glassdoor.ca/",
        "de": "https://www.glassdoor.de/",
        "fr": "https://www.glassdoor.fr/",
        "sg": "https://www.glassdoor.sg/",
        "in": "https://www.glassdoor.co.in/",
        "au": "https://www.glassdoor.com.au/",
        "nl": "https://www.glassdoor.nl/",
        "ie": "https://www.glassdoor.ie/",
    }
    return region_map.get(region, "https://www.glassdoor.com/")


def _resolve_platform_profile(platform: str) -> tuple[Path, str]:
    platform_key = platform.strip().upper()
    default_user_data_dir = (os.getenv("USER_DATA_DIR") or "./.chrome-profile").strip()
    default_profile_dir = (os.getenv("CHROME_PROFILE_DIRECTORY") or "Default").strip() or "Default"
    platform_user_data_dir = (os.getenv(f"{platform_key}_USER_DATA_DIR") or "").strip()
    platform_profile_dir = (os.getenv(f"{platform_key}_CHROME_PROFILE_DIRECTORY") or "").strip()

    conventional_platform_dir = f"./.chrome-profile-{platform.lower()}"
    if (
        platform_user_data_dir in ("", default_user_data_dir)
        and Path(conventional_platform_dir).exists()
    ):
        platform_user_data_dir = conventional_platform_dir

    user_data_dir = Path(platform_user_data_dir or default_user_data_dir)
    profile_dir = platform_profile_dir or default_profile_dir
    return user_data_dir, profile_dir


def get_profile_info(platform: str) -> dict:
    user_data_dir, profile_dir = _resolve_platform_profile(platform)
    info = {
        "platform": platform,
        "path": str(user_data_dir.resolve()),
        "profile_directory": profile_dir,
        "exists": user_data_dir.exists(),
        "size_mb": 0.0,
        "age_days": 0.0,
        "created_at": None,
        "last_used": None,
    }
    if not user_data_dir.exists():
        return info

    try:
        total_size = sum(
            item.stat().st_size for item in user_data_dir.rglob("*") if item.is_file()
        )
        info["size_mb"] = round(total_size / (1024 * 1024), 1)
        ctime = user_data_dir.stat().st_ctime
        info["created_at"] = datetime.fromtimestamp(ctime).isoformat()
        info["age_days"] = round((time.time() - ctime) / 86400, 1)

        cookie_candidates = (
            user_data_dir / profile_dir / "Cookies",
            user_data_dir / profile_dir / "Network" / "Cookies",
        )
        cookies_file = next((path for path in cookie_candidates if path.exists()), None)
        if cookies_file:
            info["last_used"] = datetime.fromtimestamp(
                cookies_file.stat().st_mtime
            ).isoformat()
    except Exception as e:
        logger.debug(f"Profile info error for {platform}: {e}")
    return info


def list_all_profiles() -> list[dict]:
    return [get_profile_info(platform) for platform in ("linkedin", "indeed", "glassdoor")]


def backup_profile(platform: str) -> Optional[str]:
    user_data_dir, _ = _resolve_platform_profile(platform)
    if not user_data_dir.exists():
        logger.debug(f"No profile to backup for {platform}: {user_data_dir}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = user_data_dir.with_name(f"{user_data_dir.name}.bak_{timestamp}")
    try:
        shutil.move(str(user_data_dir), str(backup_path))
        _record_profile_event(platform, "backup", str(backup_path))
        logger.success(f"Profile {platform} backed up to {backup_path}")
        return str(backup_path)
    except Exception as e:
        logger.error(f"Backup failed for {platform}: {e}")
        return None


def reset_profile(platform: str, launch_chrome: bool = True) -> dict:
    user_data_dir, profile_dir = _resolve_platform_profile(platform)
    result = {
        "success": False,
        "backup_path": None,
        "profile_path": str(user_data_dir.resolve()),
        "profile_directory": profile_dir,
        "chrome_pid": None,
        "message": "",
    }

    backup_path = backup_profile(platform)
    if backup_path:
        result["backup_path"] = backup_path

    try:
        user_data_dir.mkdir(parents=True, exist_ok=True)
        (user_data_dir / profile_dir).mkdir(parents=True, exist_ok=True)
        _record_profile_event(platform, "reset", str(user_data_dir))
    except Exception as e:
        result["message"] = f"Create profile failed: {e}"
        logger.error(result["message"])
        return result

    if not launch_chrome:
        result["success"] = True
        result["message"] = "Profile reset OK. Launch Chrome manually if needed."
        return result

    chrome_path = find_chrome_binary()
    if not chrome_path:
        result["success"] = True
        result["message"] = "Profile reset OK. Chrome not found for auto-launch."
        return result

    target_url = {
        "linkedin": "https://www.linkedin.com/jobs/",
        "indeed": "https://www.indeed.com/",
    }.get(platform.lower(), "")
    if platform.lower() == "glassdoor":
        target_url = _resolve_glassdoor_target_url()
    if not target_url:
        target_url = f"https://www.{platform.lower()}.com/"

    try:
        args = [
            chrome_path,
            f"--user-data-dir={user_data_dir.resolve()}",
            f"--profile-directory={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
            target_url,
        ]
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        result["success"] = True
        result["chrome_pid"] = process.pid
        result["message"] = (
            f"Chrome launched (PID {process.pid}). Complete login/setup, browse a few jobs, then close Chrome."
        )
        _record_profile_event(platform, "chrome_launched", str(process.pid))
        logger.success(f"Chrome launched for {platform} profile setup (PID {process.pid})")
        return result
    except Exception as e:
        result["message"] = f"Chrome launch failed: {e}"
        logger.error(result["message"])
        return result


def _record_profile_event(platform: str, event: str, detail: str = ""):
    try:
        PROFILE_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        if PROFILE_REGISTRY.exists():
            data = json.loads(PROFILE_REGISTRY.read_text(encoding="utf-8"))
        else:
            data = {"events": []}
        data["events"].append(
            {
                "timestamp": int(time.time()),
                "platform": platform,
                "event": event,
                "detail": detail,
            }
        )
        data["events"] = data["events"][-100:]
        PROFILE_REGISTRY.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Record profile event failed: {e}")


def get_profile_history(platform: Optional[str] = None) -> list[dict]:
    if not PROFILE_REGISTRY.exists():
        return []
    try:
        data = json.loads(PROFILE_REGISTRY.read_text(encoding="utf-8"))
        events = data.get("events", [])
        if platform:
            events = [event for event in events if event.get("platform") == platform]
        return events
    except Exception:
        return []


def cleanup_old_backups(keep_count: int = 3) -> int:
    deleted = 0
    for platform in ("linkedin", "indeed", "glassdoor"):
        user_data_dir, _ = _resolve_platform_profile(platform)
        parent = user_data_dir.parent
        prefix = f"{user_data_dir.name}.bak_"
        try:
            backups = sorted(
                [path for path in parent.iterdir() if path.name.startswith(prefix)],
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for old_backup in backups[max(0, keep_count):]:
                try:
                    if old_backup.is_dir():
                        shutil.rmtree(old_backup)
                    else:
                        old_backup.unlink()
                    deleted += 1
                    logger.info(f"Deleted old backup: {old_backup}")
                except Exception as e:
                    logger.debug(f"Delete backup failed: {e}")
        except Exception as e:
            logger.debug(f"Cleanup backup error for {platform}: {e}")
    return deleted
