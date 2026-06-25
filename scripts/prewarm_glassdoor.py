"""Open Glassdoor with the same Chrome profile used by the bot for manual prewarm."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def _resolve_profile() -> tuple[str, str]:
    user_data_dir = (
        os.getenv("GLASSDOOR_USER_DATA_DIR")
        or os.getenv("USER_DATA_DIR")
        or "./.chrome-profile-glassdoor"
    ).strip()
    profile_dir = (
        os.getenv("GLASSDOOR_CHROME_PROFILE_DIRECTORY")
        or os.getenv("CHROME_PROFILE_DIRECTORY")
        or "Default"
    ).strip()

    if user_data_dir in ("", "./.chrome-profile"):
        platform_dir = "./.chrome-profile-glassdoor"
        if Path(platform_dir).exists() or not Path(user_data_dir).exists():
            user_data_dir = platform_dir
    return user_data_dir, profile_dir


def _resolve_start_url() -> str:
    region = (os.getenv("GLASSDOOR_REGION") or "").strip().lower()
    if not region:
        config_path = PROJECT_ROOT / "config.yaml"
        try:
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
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
        "us": "https://www.glassdoor.com",
        "uk": "https://www.glassdoor.co.uk",
        "ca": "https://www.glassdoor.ca",
        "de": "https://www.glassdoor.de",
        "fr": "https://www.glassdoor.fr",
        "sg": "https://www.glassdoor.sg",
        "in": "https://www.glassdoor.co.in",
        "au": "https://www.glassdoor.com.au",
        "nl": "https://www.glassdoor.nl",
        "ie": "https://www.glassdoor.ie",
    }
    return region_map.get(region, "https://www.glassdoor.com")


def main() -> int:
    print("=" * 60)
    print("Glassdoor Browser Pre-Warm Script")
    print("=" * 60)
    print("This opens Chrome with the same Glassdoor profile the bot will reuse.")
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
    start_url = _resolve_start_url()

    print()
    print(f"Using user data dir : {abs_profile}")
    print(f"Using profile dir   : {profile_dir}")
    print(f"Opening URL         : {start_url}")
    print()

    driver = None
    try:
        driver = build_driver(
            headless=False,
            user_data_dir=user_data_dir,
            version_main=int(os.getenv("CHROME_VERSION_MAIN") or 0) or None,
            profile_directory=profile_dir,
        )
        driver.get(start_url)
        print("=" * 60)
        print("BROWSER OPEN")
        print("=" * 60)
        print("1. Solve Cloudflare if shown")
        print("2. Sign in to Glassdoor if needed")
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
    print("Glassdoor profile is now warmed and can be reused by the bot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
