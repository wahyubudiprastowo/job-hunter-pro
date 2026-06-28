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
import time
import threading
from contextlib import contextmanager
from pathlib import Path
from loguru import logger


_DRIVER_START_LOCK = threading.Lock()
_DRIVER_START_LOCK_FILE = Path("data/.control/chromedriver_start.lock")


@contextmanager
def _driver_start_guard():
    """Serialize UC's shared patcher across threads and worker processes."""
    _DRIVER_START_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _DRIVER_START_LOCK:
        with _DRIVER_START_LOCK_FILE.open("a+b") as lock_file:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)

            if os.name == "nt":
                import msvcrt
                deadline = time.time() + 120
                while True:
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.time() >= deadline:
                            raise TimeoutError(
                                "Timed out waiting for ChromeDriver startup lock"
                            )
                        time.sleep(0.2)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                lock_file.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def build_driver(headless: bool = False, user_data_dir: str = None,
                 version_main: int = None, profile_directory: str = None):
    """Build undetected Chrome driver with speed optimizations."""
    import undetected_chromedriver as uc
    from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
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
    retries = max(1, int(os.getenv("CHROME_STARTUP_RETRIES", "2") or "2"))
    last_error = None
    resolved_profile = str(Path(user_data_dir).resolve()) if user_data_dir else "(temporary)"
    logger.info(
        f"Launching Chrome (headless={headless}, profile={resolved_profile}, "
        f"profile_dir={profile_directory or 'Default'})"
    )
    # undetected-chromedriver uses one shared patched executable. Serializing
    # only construction prevents parallel workers from racing its rename step.
    with _driver_start_guard():
        for attempt in range(1, retries + 1):
            launch_kwargs = dict(kwargs)
            if attempt > 1:
                # Some local Chrome builds attach more reliably when UC owns a subprocess.
                launch_kwargs["use_subprocess"] = True
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    driver = uc.Chrome(**launch_kwargs)
                break
            except (FileExistsError, SessionNotCreatedException, WebDriverException) as e:
                last_error = e
                message = str(e)
                recoverable = (
                    isinstance(e, FileExistsError)
                    or "cannot connect to chrome" in message.lower()
                    or "chrome not reachable" in message.lower()
                    or "session not created" in message.lower()
                )
                if attempt >= retries or not recoverable:
                    raise
                logger.warning(
                    f"Chrome startup failed on attempt {attempt}/{retries}: {e}. "
                    "Retrying once; close any Chrome window using this bot profile if it repeats."
                )
                time.sleep(2)
        else:
            raise last_error

    driver.set_page_load_timeout(30)
    return driver
