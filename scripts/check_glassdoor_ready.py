"""
Glassdoor pre-flight check using the same profile resolution as the app.

Usage:
    python scripts/check_glassdoor_ready.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from packages.stealth.profile_manager import get_profile_info


def _profile_paths() -> tuple[dict, Path, str]:
    info = get_profile_info("glassdoor")
    profile_path = Path(info["path"])
    profile_dir = info.get("profile_directory") or "Default"
    return info, profile_path, profile_dir


def check_profile_directory() -> tuple[bool, str]:
    info, profile_path, profile_dir = _profile_paths()
    if not info.get("exists"):
        return False, "Profile directory not found. Run prewarm script."
    default_dir = profile_path / profile_dir
    if not default_dir.exists():
        return False, f"Profile directory '{profile_dir}' missing. Profile incomplete."
    return True, f"Profile exists at {profile_path.resolve()}"


def check_profile_size() -> tuple[bool, str]:
    info, _profile_path, _profile_dir = _profile_paths()
    size_mb = float(info.get("size_mb") or 0.0)
    if size_mb < 10:
        return False, f"Profile too small ({size_mb:.1f} MB). Re-run prewarm."
    if size_mb < 50:
        return False, f"Profile still small ({size_mb:.1f} MB). Session may be incomplete."
    return True, f"Profile size OK ({size_mb:.1f} MB)"


def check_cookies_file() -> tuple[bool, str]:
    _info, profile_path, profile_dir = _profile_paths()
    cookie_candidates = [
        profile_path / profile_dir / "Cookies",
        profile_path / profile_dir / "Network" / "Cookies",
    ]
    cookies_file = next((path for path in cookie_candidates if path.exists()), None)
    if cookies_file is None:
        return False, "Cookies file not found. No saved session detected."
    cookies_size_kb = cookies_file.stat().st_size / 1024
    if cookies_size_kb < 50:
        return False, f"Cookies file too small ({cookies_size_kb:.1f} KB). Login may not be saved."
    return True, f"Cookies file OK ({cookies_size_kb:.1f} KB) at {cookies_file.parent.name}"


def check_login_data() -> tuple[bool, str]:
    _info, profile_path, profile_dir = _profile_paths()
    login_file = profile_path / profile_dir / "Login Data"
    if not login_file.exists():
        return True, "Login Data optional - skipped"
    return True, "Login Data file exists"


def check_no_lock_files() -> tuple[bool, str]:
    _info, profile_path, _profile_dir = _profile_paths()
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_file = profile_path / name
        if lock_file.exists():
            return False, f"Lock file detected: {lock_file.name}. Close Chrome first."
    return True, "No active Chrome lock files"


def run_checks() -> tuple[int, list[tuple[str, bool, str]]]:
    checks = [
        ("Profile Directory", check_profile_directory),
        ("Profile Size", check_profile_size),
        ("Cookies File", check_cookies_file),
        ("Login Data", check_login_data),
        ("No Lock Files", check_no_lock_files),
    ]
    results = []
    for name, func in checks:
        ok, msg = func()
        results.append((name, ok, msg))
    passed = sum(1 for _name, ok, _msg in results if ok)
    return passed, results


def main() -> int:
    print("=" * 60)
    print("Glassdoor Pre-Flight Check")
    print("=" * 60)
    print()

    passed, results = run_checks()
    for name, ok, msg in results:
        symbol = "OK" if ok else "X"
        print(f"[{symbol}] {name}: {msg}")

    print()
    print("=" * 60)
    print(f"SUMMARY: {passed}/{len(results)} checks passed")
    print("=" * 60)

    if passed == len(results):
        print()
        print("Glassdoor profile is READY for bot scrape!")
        print("Next: click 'Scrape Glassdoor' in /discovered")
        return 0

    print()
    print("Profile NOT ready. Fix the issues above first.")
    print("Suggested flow:")
    print("  1. Close all Chrome windows using the Glassdoor profile")
    print("  2. Run: python scripts/prewarm_glassdoor.py")
    print("  3. Sign in, browse 5-10 jobs, then close Chrome")
    print("  4. Run this checker again")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
