"""
Glassdoor Pre-Warm Browser Script (Patch 33).

Run ONCE to setup Glassdoor Chrome profile with cookies + login.
After clearance, profile persists ~30 days.

Usage:
    python scripts/prewarm_glassdoor.py
"""
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 60)
    print("Glassdoor Browser Pre-Warm Script")
    print("=" * 60)
    print()
    print("This will open Chrome with Glassdoor profile.")
    print("You need to:")
    print("  1. Complete any Cloudflare verification")
    print("  2. Sign in to Glassdoor (Email/Password OR Google OAuth)")
    print("  3. Complete profile setup (CV upload, etc.)")
    print("  4. Browse 5-10 jobs naturally (looks human)")
    print("  5. Close Chrome when done")
    print()
    print("Cookies + login session persist in profile (~30 days).")
    print()
    input("Press ENTER to launch Chrome...")
    
    try:
        import undetected_chromedriver as uc
    except ImportError:
        print("ERROR: undetected_chromedriver not installed.")
        return
    
    profile_dir = os.path.abspath("./.chrome-profile-glassdoor")
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    
    print(f"\nLaunching Chrome with profile: {profile_dir}")
    
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        
        print("Opening Glassdoor homepage...")
        driver.get("https://www.glassdoor.com")
        
        print()
        print("=" * 60)
        print("BROWSER IS OPEN - Complete the following:")
        print("=" * 60)
        print("  1. Complete Cloudflare challenge if shown")
        print("  2. Sign in to Glassdoor (top right)")
        print("     - Email/Password OR")
        print("     - Sign in with Google (uses Chrome profile)")
        print("  3. Browse jobs for 1-2 minutes (looks human)")
        print("  4. Try search: \"Cloud Engineer\" in your city")
        print("  5. Close browser when satisfied")
        print()
        print("Profile + cookies will be saved automatically.")
        print("=" * 60)
        print()
        print("Waiting for you to close browser...")
        
        try:
            while True:
                try:
                    _ = driver.current_url
                    time.sleep(2)
                except Exception:
                    break
        except KeyboardInterrupt:
            pass
        
        try:
            driver.quit()
        except Exception:
            pass
        
        print()
        print("=" * 60)
        print("DONE! Glassdoor profile saved to:")
        print(f"  {profile_dir}")
        print()
        print("Bot will now reuse this profile (cookies persist ~30 days)")
        print("=" * 60)
    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    main()