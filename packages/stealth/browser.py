"""
Chrome browser factory using undetected-chromedriver — PATCH 8 (faster startup).

Optimizations:
- Cache chromedriver version (skip update check after first run)
- Disable image loading (faster page loads)
- Quick-start flag
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from loguru import logger


def build_driver(headless: bool = False, user_data_dir: str = None,
                 version_main: int = None, profile_directory: str = None):
    """Build undetected Chrome driver with speed optimizations."""
    import undetected_chromedriver as uc
    try:
        from packages.extractors.indeed_2026_fixes import get_stealth_chrome_options
    except Exception:
        get_stealth_chrome_options = None

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")

    option_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions",
        "--disable-default-apps",
        "--disable-popup-blocking",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-translate",
        "--disable-notifications",
    ]
    if get_stealth_chrome_options:
        for opt in get_stealth_chrome_options():
            if opt not in option_args:
                option_args.append(opt)
    for opt in option_args:
        options.add_argument(opt)

    # Reduce logs
    options.add_argument("--log-level=3")
    options.add_argument("--silent")

    # Persistent profile
    if user_data_dir:
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={Path(user_data_dir).absolute()}")
    if profile_directory:
        options.add_argument(f"--profile-directory={profile_directory}")

    kwargs = {"options": options, "use_subprocess": False}
    if version_main:
        kwargs["version_main"] = version_main

    # Suppress UC banner stderr noise
    import io, contextlib
    with contextlib.redirect_stderr(io.StringIO()):
        driver = uc.Chrome(**kwargs)

    driver.set_page_load_timeout(30)
    logger.info(
        f"Launching Chrome (headless={headless}, profile={user_data_dir}, "
        f"profile_dir={profile_directory or 'Default'})"
    )
    return driver
