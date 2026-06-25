"""
Glassdoor Pre-Flight Check (Patch 33.3).

Verify Glassdoor profile is ready BEFORE bot launches.
Prevents wasted runs on unprepared profiles.

Usage:
    python scripts/check_glassdoor_ready.py
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def check_profile_directory() -> tuple[bool, str]:
    """Check profile directory exists with proper structure."""
    profile_path = Path("./.chrome-profile-glassdoor")
    
    if not profile_path.exists():
        return False, "Profile directory not found. Run prewarm script."
    
    default_dir = profile_path / "Default"
    if not default_dir.exists():
        return False, "Profile Default directory missing. Profile incomplete."
    
    return True, f"Profile exists at {profile_path.absolute()}"


def check_profile_size() -> tuple[bool, str]:
    """Profile should be > 50 MB if properly setup."""
    profile_path = Path("./.chrome-profile-glassdoor")
    
    if not profile_path.exists():
        return False, "Profile not found"
    
    total_size = sum(
        f.stat().st_size for f in profile_path.rglob("*") if f.is_file()
    )
    size_mb = total_size / (1024 * 1024)
    
    if size_mb < 10:
        return False, f"Profile too small ({size_mb:.1f} MB). Re-run prewarm."
    elif size_mb < 50:
        return False, f"Profile small ({size_mb:.1f} MB). May not have full session."
    else:
        return True, f"Profile size OK ({size_mb:.1f} MB)"


def check_cookies_file() -> tuple[bool, str]:
    """Cookies file must exist with session data."""
    cookies_file = Path("./.chrome-profile-glassdoor/Default/Cookies")
    
    if not cookies_file.exists():
        return False, "Cookies file not found. No login session saved."
    
    cookies_size_kb = cookies_file.stat().st_size / 1024
    
    if cookies_size_kb < 50:
        return False, f"Cookies file too small ({cookies_size_kb:.1f} KB). Login may not be saved."
    
    return True, f"Cookies file OK ({cookies_size_kb:.1f} KB)"


def check_login_data() -> tuple[bool, str]:
    """Login Data file indicates browser was used."""
    login_file = Path("./.chrome-profile-glassdoor/Default/Login Data")
    
    if not login_file.exists():
        return True, "Login Data file optional - skipped"
    
    return True, "Login Data file exists"


def check_no_lock_files() -> tuple[bool, str]:
    """Lock files indicate Chrome is still using the profile."""
    lock_files = [
        ".chrome-profile-glassdoor/SingletonLock",
        ".chrome-profile-glassdoor/SingletonCookie",
        ".chrome-profile-glassdoor/SingletonSocket",
    ]
    
    for lock in lock_files:
        if Path(lock).exists():
            return False, f"Lock file detected: {lock}. Close Chrome first!"
    
    return True, "No active Chrome lock files"


def main():
    print("=" * 60)
    print("Glassdoor Pre-Flight Check")
    print("=" * 60)
    print()
    
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
        status = "PASS" if ok else "FAIL"
        symbol = "OK" if ok else "X"
        print(f"[{symbol}] {name}: {msg}")
        results.append((name, ok))
    
    print()
    print("=" * 60)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    print(f"SUMMARY: {passed}/{total} checks passed")
    print("=" * 60)
    
    if passed == total:
        print()
        print("Glassdoor profile is READY for bot scrape!")
        print("Next: Click 'Scrape Glassdoor' at /discovered")
        return 0
    else:
        print()
        print("Profile NOT ready. Fix the issues above first.")
        print()
        print("To prepare profile:")
        print("  1. Make sure Chrome is closed")
        print("  2. Run: python scripts/prewarm_glassdoor.py")
        print("  3. In browser: Sign in with Google, browse 5-10 jobs")
        print("  4. Close Chrome")
        print("  5. Run this check again")
        return 1


if __name__ == "__main__":
    sys.exit(main())