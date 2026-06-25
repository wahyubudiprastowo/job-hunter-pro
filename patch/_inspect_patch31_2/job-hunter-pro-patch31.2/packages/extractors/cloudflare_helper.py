"""
Cloudflare Workaround Helpers (Patch 31.2).

Realistic strategy for Indeed Cloudflare:

1. Pre-warm script — user opens browser manually, completes CF once,
   cookies saved to Chrome profile (lasts ~30 days)

2. Extended manual wait — 5 minutes (not 60s)

3. URL-based detection — wait for actual jobs URL, not just text disappear

4. Better visibility — clear instructions in log + dashboard

5. Skip-on-fail — instead of crash login, skip Indeed gracefully
"""
from __future__ import annotations
import time
from typing import Optional
from loguru import logger

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
)


def detect_cloudflare_state(driver) -> dict:
    """
    Better Cloudflare state detection.
    
    Returns dict with:
        is_challenge: bool — there is a CF challenge
        is_blocked: bool — page is "Additional Verification Required" (HARDER)
        cleared: bool — page is normal Indeed
        page_type: str — descriptive label
    """
    state = {
        "is_challenge": False,
        "is_blocked": False,
        "cleared": False,
        "page_type": "unknown",
    }
    
    try:
        current_url = driver.current_url.lower()
        page_lower = driver.page_source.lower()
        
        # Check for HARD block (Ray ID + Additional Verification)
        if ("additional verification required" in page_lower or
            "ray id" in page_lower and "verify you are human" in page_lower):
            state["is_blocked"] = True
            state["page_type"] = "blocked_with_ray_id"
            return state
        
        # Check for simple Turnstile challenge
        if ("verify you are human" in page_lower or
            "just a moment" in page_lower or
            "checking your browser" in page_lower):
            state["is_challenge"] = True
            state["page_type"] = "turnstile_challenge"
            return state
        
        # Check for cleared state — actual Indeed URL with jobs/account
        cleared_indicators = [
            "/jobs?", "/account/", "/m/myjobs", "/career-services",
            "/companies/", "/q-", "indeed.com/?from=",
        ]
        
        # Cleared if URL matches and page has Indeed UI elements
        url_matches = any(ind in current_url for ind in cleared_indicators)
        has_indeed_ui = any(marker in page_lower for marker in [
            "mosaic-jobresults", "id=\"jobsearchform\"",
            "what do you do", "sign in to access",
        ])
        
        if url_matches or has_indeed_ui:
            state["cleared"] = True
            state["page_type"] = "indeed_normal"
            return state
        
        state["page_type"] = "unknown_no_cf_no_indeed_ui"
        return state
    
    except Exception as e:
        logger.debug(f"CF detect error: {e}")
        return state


def wait_for_manual_cloudflare_v2(driver, timeout=300, poll_interval=5):
    """
    Extended manual wait for user to complete Cloudflare.
    Default 5 minutes (not 60s).
    
    Strategy:
    - Print prominent instructions
    - Poll every 5s for cleared state
    - Detect hard block early (no point waiting)
    
    Returns True if cleared, False if timeout/blocked.
    """
    logger.warning("=" * 70)
    logger.warning("🚨 CLOUDFLARE CHALLENGE DETECTED")
    logger.warning("=" * 70)
    logger.warning("")
    logger.warning("ACTION REQUIRED IN BROWSER:")
    logger.warning("  1. Click the \"Verify you are human\" checkbox")
    logger.warning("  2. Wait for page to transition to Indeed")
    logger.warning("  3. Bot will continue automatically once cleared")
    logger.warning("")
    logger.warning(f"⏰ Bot will wait up to {timeout//60} minutes...")
    logger.warning("=" * 70)
    
    end = time.time() + timeout
    last_state = None
    
    while time.time() < end:
        state = detect_cloudflare_state(driver)
        
        # Log state changes
        if state["page_type"] != last_state:
            logger.info(f"   ↳ Current page: {state['page_type']}")
            last_state = state["page_type"]
        
        # SUCCESS: page cleared
        if state["cleared"]:
            logger.success("✅ Cloudflare CLEARED — page is normal Indeed")
            time.sleep(2)
            return True
        
        # HARD BLOCK: stop waiting
        if state["is_blocked"]:
            remaining = int(end - time.time())
            if remaining > 30:  # Give user a chance to solve hard block
                logger.warning(f"⚠️  Hard block detected. Waiting {remaining}s for manual solve...")
            else:
                logger.error("❌ Hard block could not be solved")
                return False
        
        time.sleep(poll_interval)
    
    logger.error(f"⏰ Cloudflare wait timeout after {timeout}s")
    return False


def handle_cloudflare_safely(driver, timeout=300) -> bool:
    """
    Safe Cloudflare handling that does not crash login.
    
    Returns:
        True  = no challenge OR successfully cleared
        False = challenge present but could not clear
    """
    state = detect_cloudflare_state(driver)
    
    if state["cleared"] or (not state["is_challenge"] and not state["is_blocked"]):
        return True  # OK to proceed
    
    return wait_for_manual_cloudflare_v2(driver, timeout=timeout)