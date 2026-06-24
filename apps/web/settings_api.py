from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger


CONFIG_PATH = Path("config.yaml")
ENV_PATH = Path(".env")
BACKUP_DIR = Path("data/.settings_backups")


def _backup_file(path: Path, prefix: str) -> Optional[Path]:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{prefix}_{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def load_config() -> dict:
    try:
        if not CONFIG_PATH.exists():
            return {}
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.error(f"Failed to load config.yaml: {exc}")
        return {}


def save_config(data: dict) -> tuple[bool, str]:
    try:
        backup = _backup_file(CONFIG_PATH, "config")
        yaml_text = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
        )
        CONFIG_PATH.write_text(yaml_text, encoding="utf-8")
        return True, f"saved successfully (backup: {backup.name if backup else 'none'})"
    except Exception as exc:
        logger.exception("Failed to save config.yaml")
        return False, f"save failed: {exc}"


def update_config_section(section_path: str, new_values: dict) -> tuple[bool, str]:
    config = load_config()
    if not section_path:
        config.update(new_values)
        return save_config(config)

    parts = section_path.split(".")
    target = config
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    last = parts[-1]
    if isinstance(target.get(last), dict):
        target.setdefault(last, {}).update(new_values)
    else:
        target[last] = new_values
    return save_config(config)


def load_env() -> dict:
    env_vars = {}
    if not ENV_PATH.exists():
        return env_vars
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            env_vars[key.strip()] = value.strip().strip('"').strip("'")
    except Exception as exc:
        logger.error(f"Failed to load .env: {exc}")
    return env_vars


def save_env(env_vars: dict, preserve_comments: bool = True) -> tuple[bool, str]:
    try:
        backup = _backup_file(ENV_PATH, "env")
        if preserve_comments and ENV_PATH.exists():
            updated = []
            seen = set()
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    updated.append(line)
                    continue
                key, _, _ = stripped.partition("=")
                key = key.strip()
                if key in env_vars:
                    updated.append(f"{key}={env_vars[key]}")
                    seen.add(key)
                else:
                    updated.append(line)
            for key, value in env_vars.items():
                if key not in seen:
                    updated.append(f"{key}={value}")
            ENV_PATH.write_text("\n".join(updated), encoding="utf-8")
        else:
            ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in env_vars.items()), encoding="utf-8")
        return True, f"saved successfully (backup: {backup.name if backup else 'none'})"
    except Exception as exc:
        logger.exception("Failed to save .env")
        return False, f"save failed: {exc}"


def mask_secret(value: str, visible_chars: int = 4) -> str:
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
    env = load_env()
    display = {}
    for key, value in env.items():
        display[key] = {
            "value": mask_secret(value) if key in SECRET_KEYS else value,
            "is_secret": key in SECRET_KEYS,
            "has_value": bool(value),
        }
    return display


def validate_config(data: dict) -> list[str]:
    warnings = []
    required = ["mode", "platforms", "personal", "resume", "ai", "stealth"]
    for key in required:
        if key not in data:
            warnings.append(f"Missing required section: {key}")
    platforms = data.get("platforms", {}) or {}
    enabled = [name for name, cfg in platforms.items() if cfg.get("enabled", False)]
    if not enabled:
        warnings.append("No platforms enabled - bot will not run")
    ai_cfg = data.get("ai", {}) or {}
    if ai_cfg.get("enabled", False):
        if not ai_cfg.get("model"):
            warnings.append("AI enabled but no model specified")
        if not (ai_cfg.get("base_url") or os.getenv("AI_BASE_URL")):
            warnings.append("AI enabled but no base_url in config or env")
    resume_path = (data.get("resume", {}) or {}).get("default_path", "")
    if resume_path and not Path(resume_path).exists():
        warnings.append(f"Resume file not found: {resume_path}")
    return warnings
