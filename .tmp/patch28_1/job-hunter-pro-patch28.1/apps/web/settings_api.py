"""
Settings API (Patch 28.1).

Handles reading/writing config.yaml and .env safely.
Provides validation, backup, and rollback.
"""
from __future__ import annotations
import os
import re
import shutil
import yaml
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from loguru import logger

CONFIG_PATH = Path("config.yaml")
ENV_PATH = Path(".env")
BACKUP_DIR = Path("data/.settings_backups")


def _backup_file(path: Path, prefix: str) -> Optional[Path]:
    """Create timestamped backup before modification."""
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{prefix}_{ts}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def load_config() -> dict:
    """Load config.yaml as dict."""
    try:
        if not CONFIG_PATH.exists():
            return {}
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def save_config(data: dict) -> tuple[bool, str]:
    """Save config dict to config.yaml with backup."""
    try:
        backup = _backup_file(CONFIG_PATH, "config")
        
        # Pretty YAML output
        yaml_str = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
        )
        CONFIG_PATH.write_text(yaml_str, encoding="utf-8")
        
        logger.info(f"Config saved (backup: {backup})")
        return True, f"Saved successfully (backup: {backup.name if backup else None})"
    except Exception as e:
        logger.exception("Failed to save config")
        return False, f"Save failed: {e}"


def update_config_section(section_path: str, new_values: dict) -> tuple[bool, str]:
    """
    Update a section of config.yaml.
    
    Args:
        section_path: Dot-separated path like "ai" or "platforms.linkedin"
        new_values: Dict to merge into that section
    
    Returns:
        (success, message)
    """
    config = load_config()
    
    # Navigate to section
    parts = section_path.split(".") if section_path else []
    target = config
    for part in parts[:-1]:
        if part not in target:
            target[part] = {}
        target = target[part]
    
    if parts:
        last = parts[-1]
        if last not in target:
            target[last] = {}
        # Merge new values
        if isinstance(target[last], dict):
            target[last].update(new_values)
        else:
            target[last] = new_values
    else:
        # Root-level merge
        config.update(new_values)
    
    return save_config(config)


def load_env() -> dict:
    """Parse .env file into dict."""
    env_vars = {}
    if not ENV_PATH.exists():
        return env_vars
    
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
    except Exception as e:
        logger.error(f"Failed to load .env: {e}")
    
    return env_vars


def save_env(env_vars: dict, preserve_comments: bool = True) -> tuple[bool, str]:
    """
    Save .env with optional comment preservation.
    
    Reads existing file, updates only the keys provided,
    keeps all comments and structure intact.
    """
    try:
        backup = _backup_file(ENV_PATH, "env")
        
        if preserve_comments and ENV_PATH.exists():
            # Read existing lines and update in-place
            new_lines = []
            updated_keys = set()
            
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    new_lines.append(line)
                    continue
                
                key, _, _ = stripped.partition("=")
                key = key.strip()
                
                if key in env_vars:
                    # Mask preserve original quoting style
                    value = env_vars[key]
                    new_lines.append(f"{key}={value}")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            
            # Append any new keys not in original file
            for key, value in env_vars.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}")
            
            ENV_PATH.write_text("\n".join(new_lines), encoding="utf-8")
        else:
            # Simple write
            lines = [f"{k}={v}" for k, v in env_vars.items()]
            ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
        
        logger.info(f".env saved (backup: {backup})")
        return True, f"Saved successfully (backup: {backup.name if backup else None})"
    except Exception as e:
        logger.exception("Failed to save .env")
        return False, f"Save failed: {e}"


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Mask secret values for safe display."""
    if not value:
        return ""
    if len(value) <= visible_chars * 2:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars * 2) + value[-visible_chars:]


SECRET_KEYS = {
    "LINKEDIN_PASSWORD",
    "INDEED_PASSWORD",
    "AI_API_KEY",
    "FLASK_SECRET_KEY",
    "LINKEDIN_TOTP_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "CAPTCHA_API_KEY",
    "SMTP_PASSWORD",
    "TEAMS_WEBHOOK_URL",
    "DISCORD_WEBHOOK_URL",
}


def get_env_for_display() -> dict:
    """Get .env vars with secrets masked for safe display."""
    env = load_env()
    display = {}
    for key, value in env.items():
        if key in SECRET_KEYS:
            display[key] = {"value": mask_secret(value), "is_secret": True, "has_value": bool(value)}
        else:
            display[key] = {"value": value, "is_secret": False, "has_value": bool(value)}
    return display


def validate_config(data: dict) -> list[str]:
    """Validate config structure. Returns list of warnings/errors."""
    warnings = []
    
    # Check required top-level keys
    required = ["mode", "platforms", "personal", "resume", "ai", "stealth"]
    for key in required:
        if key not in data:
            warnings.append(f"Missing required section: {key}")
    
    # Check at least one platform enabled
    platforms = data.get("platforms", {})
    enabled = [p for p, cfg in platforms.items() if cfg.get("enabled", False)]
    if not enabled:
        warnings.append("No platforms enabled — bot will not run")
    
    # Check AI config if enabled
    if data.get("ai", {}).get("enabled", False):
        ai_cfg = data.get("ai", {})
        if not ai_cfg.get("model"):
            warnings.append("AI enabled but no model specified")
        if not (ai_cfg.get("base_url") or os.getenv("AI_BASE_URL")):
            warnings.append("AI enabled but no base_url (config or env)")
    
    # Resume file check
    resume_path = data.get("resume", {}).get("default_path", "")
    if resume_path and not Path(resume_path).exists():
        warnings.append(f"Resume file not found: {resume_path}")
    
    return warnings