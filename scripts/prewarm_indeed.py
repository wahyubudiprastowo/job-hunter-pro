"""Open Indeed with the same Chrome profile used by the bot for manual prewarm."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def _resolve_profile() -> tuple[str, str]:
    user_data_dir = (
        os.getenv("INDEED_USER_DATA_DIR")
        or os.getenv("USER_DATA_DIR")
        or "./.chrome-profile-indeed"
    ).strip()
    profile_dir = (
        os.getenv("INDEED_CHROME_PROFILE_DIRECTORY")
        or os.getenv("CHROME_PROFILE_DIRECTORY")
        or "Default"
    ).strip()

    if user_data_dir in ("", "./.chrome-profile"):
        platform_dir = "./.chrome-profile-indeed"
        if Path(platform_dir).exists() or not Path(user_data_dir).exists():
            user_data_dir = platform_dir
    return user_data_dir, profile_dir


def main() -> int:
    print("=" * 60)
    print("Indeed Browser Pre-Warm Script")
    print("=" * 60)
    print("This opens Chrome with the same profile the bot should reuse.")
    print("Complete Cloudflare manually, sign in, browse jobs for 1-2 minutes,")
    print("then close the browser window.")
    print()
    input("Press ENTER to launch Chrome...")

    try:
        from packages.stealth.browser import build_driver
    except Exception as e:
        print(f"ERROR: could not import build_driver: {e}")
        return 1

    user_data_dir, profile_dir = _resolve_profile()
    abs_profile = str((PROJECT_ROOT / user_data_dir).resolve()) if not os.path.isabs(user_data_dir) else user_data_dir
    Path(abs_profile).mkdir(parents=True, exist_ok=True)

    print()
    print(f"Using user data dir : {abs_profile}")
    print(f"Using profile dir   : {profile_dir}")
    print()

    driver = None
    try:
        driver = build_driver(
            headless=False,
            user_data_dir=user_data_dir,
            version_main=int(os.getenv("CHROME_VERSION_MAIN") or 0) or None,
            profile_directory=profile_dir,
        )
        driver.get("https://www.indeed.com")
        print("=" * 60)
        print("BROWSER OPEN")
        print("=" * 60)
        print("1. Solve Cloudflare if shown")
        print("2. Sign in to Indeed if needed")
        print("3. Browse a few pages and run one search manually")
        print("4. Close the browser when done")
        print("=" * 60)

        while True:
            try:
                _ = driver.current_url
                time.sleep(2)
            except Exception:
                break
    except KeyboardInterrupt:
        print("\nInterrupted, closing browser...")
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Profile is now warmed and can be reused by the bot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
