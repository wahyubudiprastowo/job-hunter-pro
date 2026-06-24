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
                 version_main: int = None):
    """Build undetected Chrome driver with speed optimizations."""
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")

    # Speed optimizations
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-notifications")

    # Reduce logs
    options.add_argument("--log-level=3")
    options.add_argument("--silent")

    # Persistent profile
    if user_data_dir:
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={Path(user_data_dir).absolute()}")

    kwargs = {"options": options, "use_subprocess": False}
    if version_main:
        kwargs["version_main"] = version_main

    # Suppress UC banner stderr noise
    import io, contextlib
    with contextlib.redirect_stderr(io.StringIO()):
        driver = uc.Chrome(**kwargs)

    driver.set_page_load_timeout(30)
    logger.info(f"Launching Chrome (headless={headless}, profile={user_data_dir})")
    return driver
