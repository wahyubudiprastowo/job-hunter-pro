"""
Indeed Pre-Warm Browser Script (Patch 31.2).

Run this ONCE manually to setup Indeed Chrome profile.
After clearance, cookies persist for ~30 days.

Usage:
    python scripts/prewarm_indeed.py
"""
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 60)
    print("Indeed Browser Pre-Warm Script")
    print("=" * 60)
    print()
    print("This script will open Chrome with Indeed profile.")
    print("You need to:")
    print("  1. Complete any Cloudflare verification")
    print("  2. Sign in to Indeed if not logged in")
    print("  3. Browse a few jobs (looks more human)")
    print("  4. Close browser when done")
    print()
    print("After this, Indeed cookies will be saved in Chrome profile.")
    print("Bot will reuse this profile and skip Cloudflare!")
    print()
    input("Press ENTER to launch Chrome...")
    
    try:
        import undetected_chromedriver as uc
    except ImportError:
        print("ERROR: undetected_chromedriver not installed.")
        print("Run: pip install undetected-chromedriver")
        return
    
    # Use same profile as bot
    profile_dir = os.path.abspath("./.chrome-profile-indeed")
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    
    print(f"\nLaunching Chrome with profile: {profile_dir}")
    print()
    
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        })
        
        # Navigate to Indeed
        print("Opening Indeed homepage...")
        driver.get("https://www.indeed.com")
        
        print()
        print("=" * 60)
        print("BROWSER IS OPEN — Complete the following:")
        print("=" * 60)
        print("  1. Complete any Cloudflare challenge if shown")
        print("  2. Sign in to Indeed (top right)")
        print("  3. Browse jobs for 1-2 minutes (looks human)")
        print("  4. Try a search: \"Cloud Engineer\" in your city")
        print("  5. Close browser when satisfied")
        print()
        print("Cookies and profile will be saved automatically.")
        print("=" * 60)
        print()
        print("Waiting for you to close browser...")
        
        # Wait for user to close browser
        try:
            while True:
                try:
                    _ = driver.current_url
                    time.sleep(2)
                except Exception:
                    break
        except KeyboardInterrupt:
            print("\nInterrupted. Closing...")
        
        try:
            driver.quit()
        except Exception:
            pass
        
        print()
        print("=" * 60)
        print("DONE! Indeed profile saved to:")
        print(f"  {profile_dir}")
        print()
        print("Bot will now reuse this profile (cookies persist ~30 days)")
        print("=" * 60)
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()