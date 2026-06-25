"""
Chrome Profile Manager (Patch 32.3).

Provides safe profile reset workflow:
1. Backup flagged profile with timestamp
2. Create fresh profile directory
3. Launch Chrome for manual login/setup
4. Track profile age for proactive rotation

Used when Cloudflare/anti-bot detection requires fresh fingerprint.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger


PROFILE_REGISTRY = Path("data/.control/profile_registry.json")


def find_chrome_binary() -> Optional[str]:
    """Find Chrome executable on Windows."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    
    return None


def get_profile_path(platform: str) -> Path:
    """Get profile path for platform (linkedin/indeed)."""
    return Path(f".chrome-profile-{platform.lower()}")


def get_profile_info(platform: str) -> dict:
    """Get info about platform profile."""
    profile_path = get_profile_path(platform)
    
    info = {
        "platform": platform,
        "path": str(profile_path.absolute()),
        "exists": profile_path.exists(),
        "size_mb": 0,
        "age_days": 0,
        "created_at": None,
        "last_used": None,
    }
    
    if profile_path.exists():
        try:
            # Profile size
            total_size = sum(
                f.stat().st_size for f in profile_path.rglob("*") if f.is_file()
            )
            info["size_mb"] = round(total_size / (1024 * 1024), 1)
            
            # Profile age (from creation time)
            ctime = profile_path.stat().st_ctime
            info["created_at"] = datetime.fromtimestamp(ctime).isoformat()
            info["age_days"] = round((time.time() - ctime) / 86400, 1)
            
            # Last used (from Default/Cookies modify time if exists)
            cookies_file = profile_path / "Default" / "Cookies"
            if cookies_file.exists():
                mtime = cookies_file.stat().st_mtime
                info["last_used"] = datetime.fromtimestamp(mtime).isoformat()
        except Exception as e:
            logger.debug(f"Profile info error for {platform}: {e}")
    
    return info


def list_all_profiles() -> list:
    """List all known platform profiles + their info."""
    return [get_profile_info(p) for p in ["linkedin", "indeed"]]


def backup_profile(platform: str) -> Optional[str]:
    """
    Backup current profile with timestamp.
    Returns backup path or None if no profile exists.
    """
    profile_path = get_profile_path(platform)
    
    if not profile_path.exists():
        logger.debug(f"No profile to backup: {profile_path}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = profile_path.with_name(f"{profile_path.name}.bak_{timestamp}")
    
    try:
        # Use shutil.move (atomic on same drive)
        shutil.move(str(profile_path), str(backup_path))
        logger.success(f"Profile {platform} backed up to: {backup_path}")
        
        # Record in registry
        _record_profile_event(platform, "backup", str(backup_path))
        
        return str(backup_path)
    except Exception as e:
        logger.error(f"Backup failed for {platform}: {e}")
        return None


def reset_profile(platform: str, launch_chrome: bool = True) -> dict:
    """
    Reset platform profile: backup old, create fresh, optionally launch Chrome.
    
    Returns:
        dict with: success, backup_path, profile_path, chrome_pid (if launched)
    """
    result = {
        "success": False,
        "backup_path": None,
        "profile_path": None,
        "chrome_pid": None,
        "message": "",
    }
    
    profile_path = get_profile_path(platform)
    
    # Step 1: Backup existing profile
    backup = backup_profile(platform)
    if backup:
        result["backup_path"] = backup
    
    # Step 2: Create fresh profile directory
    try:
        profile_path.mkdir(parents=True, exist_ok=True)
        (profile_path / "Default").mkdir(parents=True, exist_ok=True)
        result["profile_path"] = str(profile_path.absolute())
        logger.info(f"Created fresh profile: {profile_path}")
        _record_profile_event(platform, "reset", str(profile_path))
    except Exception as e:
        result["message"] = f"Create profile failed: {e}"
        logger.error(result["message"])
        return result
    
    # Step 3: Launch Chrome for manual setup
    if launch_chrome:
        chrome_path = find_chrome_binary()
        if not chrome_path:
            result["message"] = "Chrome not found. Profile reset OK, but manual launch needed."
            logger.warning(result["message"])
            result["success"] = True
            return result
        
        try:
            # Launch Chrome with new profile, navigate to platform homepage
            url = f"https://www.{platform.lower()}.com"
            args = [
                chrome_path,
                f"--user-data-dir={profile_path.absolute()}",
                "--profile-directory=Default",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized",
                url,
            ]
            
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            result["chrome_pid"] = process.pid
            result["success"] = True
            result["message"] = (
                f"Chrome launched (PID {process.pid}). "
                f"Complete Cloudflare verification and login to {platform}, "
                f"browse 5-10 jobs, then close Chrome."
            )
            logger.success(f"Chrome launched for {platform} setup (PID {process.pid})")
            _record_profile_event(platform, "chrome_launched", str(process.pid))
        except Exception as e:
            result["message"] = f"Chrome launch failed: {e}"
            logger.error(result["message"])
            return result
    else:
        result["success"] = True
        result["message"] = "Profile reset OK. Launch Chrome manually if needed."
    
    return result


def _record_profile_event(platform: str, event: str, detail: str = ""):
    """Record profile management event in registry."""
    try:
        PROFILE_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing
        if PROFILE_REGISTRY.exists():
            data = json.loads(PROFILE_REGISTRY.read_text(encoding="utf-8"))
        else:
            data = {"events": []}
        
        # Append event
        data["events"].append({
            "timestamp": int(time.time()),
            "platform": platform,
            "event": event,
            "detail": detail,
        })
        
        # Keep only last 100 events
        data["events"] = data["events"][-100:]
        
        PROFILE_REGISTRY.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Record event failed: {e}")


def get_profile_history(platform: Optional[str] = None) -> list:
    """Get profile management history."""
    if not PROFILE_REGISTRY.exists():
        return []
    
    try:
        data = json.loads(PROFILE_REGISTRY.read_text(encoding="utf-8"))
        events = data.get("events", [])
        
        if platform:
            events = [e for e in events if e.get("platform") == platform]
        
        return events
    except Exception:
        return []


def cleanup_old_backups(keep_count: int = 3) -> int:
    """
    Keep only N most recent backups per platform.
    Returns count of deleted backups.
    """
    deleted = 0
    
    for platform in ["linkedin", "indeed"]:
        profile_path = get_profile_path(platform)
        parent = profile_path.parent
        prefix = f"{profile_path.name}.bak_"
        
        try:
            # Find all backups
            backups = sorted(
                [p for p in parent.iterdir() if p.name.startswith(prefix)],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            
            # Delete excess (keep newest N)
            for old_backup in backups[keep_count:]:
                try:
                    shutil.rmtree(str(old_backup))
                    deleted += 1
                    logger.info(f"Deleted old backup: {old_backup.name}")
                except Exception as e:
                    logger.debug(f"Delete backup failed: {e}")
        except Exception as e:
            logger.debug(f"Cleanup error for {platform}: {e}")
    
    return deleted