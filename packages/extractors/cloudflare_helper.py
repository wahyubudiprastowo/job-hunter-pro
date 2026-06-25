"""Pragmatic Cloudflare helpers for Indeed manual/prewarm flow."""
from __future__ import annotations

import time
from urllib.parse import urlparse

from loguru import logger

from packages.extractors.indeed_2026_fixes import handle_cloudflare_if_present


def detect_cloudflare_state(driver) -> dict:
    """Return normalized Cloudflare/Indeed page state."""
    state = {
        "is_challenge": False,
        "is_blocked": False,
        "cleared": False,
        "page_type": "unknown",
    }
    try:
        current_url = (driver.current_url or "").lower()
        page_lower = (driver.page_source or "").lower()
    except Exception:
        return state

    hard_block_markers = [
        "additional verification required",
        "ray id",
        "return home",
    ]
    if any(marker in page_lower for marker in hard_block_markers) and "verify you are human" in page_lower:
        state["is_challenge"] = True
        state["is_blocked"] = True
        state["page_type"] = "blocked_with_ray_id"
        return state

    challenge_markers = [
        "verify you are human",
        "just a moment",
        "checking your browser",
        "challenge-platform",
        "turnstile",
    ]
    if any(marker in page_lower for marker in challenge_markers):
        state["is_challenge"] = True
        state["page_type"] = "turnstile_challenge"
        return state

    cleared_url_markers = [
        "/jobs",
        "/account/",
        "/m/myjobs",
        "/career-services",
        "/companies/",
        "indeed.com/?from=",
    ]
    indeed_ui_markers = [
        "jobsearchform",
        "mosaic-jobresults",
        "find jobs",
        "find salaries",
        "company reviews",
        "upload your resume",
    ]
    if any(marker in current_url for marker in cleared_url_markers) or any(marker in page_lower for marker in indeed_ui_markers):
        state["cleared"] = True
        state["page_type"] = "indeed_normal"
        return state

    if "indeed.com" in current_url and "not found" not in page_lower:
        state["cleared"] = True
        state["page_type"] = "indeed_home"
        return state

    return state


def _restore_url_if_needed(driver, return_to_url: str | None) -> None:
    if not return_to_url:
        return
    try:
        current_url = (driver.current_url or "").rstrip("/")
    except Exception:
        current_url = ""
    if not current_url:
        return
    try:
        current_host = urlparse(current_url).netloc.lower()
        target_host = urlparse(return_to_url).netloc.lower()
    except Exception:
        current_host = ""
        target_host = ""
    page_lower = (driver.page_source or "").lower()
    if current_host != target_host:
        return
    if current_url.lower() == return_to_url.rstrip("/").lower():
        return
    if "additional verification required" in page_lower:
        return
    if "not found" in page_lower and "/account/settings" in current_url.lower():
        logger.info(f"Cloudflare cleared - restoring target URL: {return_to_url}")
        driver.get(return_to_url)
        time.sleep(3)
        return
    if any(marker in current_url.lower() for marker in ["/", "/?from=", "/account/login"]) and return_to_url.rstrip("/").lower() != current_url.lower():
        logger.info(f"Cloudflare cleared - restoring target URL: {return_to_url}")
        driver.get(return_to_url)
        time.sleep(3)


def wait_for_manual_cloudflare_v2(driver, timeout: int = 300, poll_interval: int = 5, return_to_url: str | None = None) -> bool:
    logger.warning("=" * 70)
    logger.warning("CLOUDFLARE CHALLENGE DETECTED")
    logger.warning("=" * 70)
    logger.warning("Action in browser:")
    logger.warning("  1. Complete the Cloudflare verification manually")
    logger.warning("  2. Wait for page transition to normal Indeed")
    logger.warning("  3. Bot will continue automatically")
    logger.warning(f"Bot will wait up to {max(1, timeout // 60)} minute(s)")
    logger.warning("If this keeps repeating, run: python scripts\\prewarm_indeed.py")
    logger.warning("=" * 70)

    end = time.time() + timeout
    last_page_type = None
    while time.time() < end:
        state = detect_cloudflare_state(driver)
        if state["page_type"] != last_page_type:
            logger.info(f"Cloudflare page state: {state['page_type']}")
            last_page_type = state["page_type"]
        if state["cleared"]:
            _restore_url_if_needed(driver, return_to_url)
            logger.success("Cloudflare cleared - continuing")
            time.sleep(2)
            return True
        if state["is_blocked"]:
            remaining = int(end - time.time())
            if remaining <= 30:
                logger.error("Hard Cloudflare block could not be solved in time")
                return False
        time.sleep(poll_interval)
    logger.error(f"Cloudflare wait timeout after {timeout}s")
    return False


def handle_cloudflare_safely(driver, timeout: int = 300, return_to_url: str | None = None) -> bool:
    """
    Keep existing auto-bypass, but fall back to realistic manual/prewarm flow.
    """
    state = detect_cloudflare_state(driver)
    if state["cleared"] or not state["is_challenge"]:
        return True

    if state["is_blocked"]:
        logger.warning("Indeed Cloudflare hard block detected (Ray ID / Additional Verification)")
        return wait_for_manual_cloudflare_v2(
            driver,
            timeout=timeout,
            poll_interval=5,
            return_to_url=return_to_url,
        )

    auto_timeout = min(timeout, 45)
    if handle_cloudflare_if_present(driver, timeout=auto_timeout, return_to_url=return_to_url):
        return True

    remaining = max(timeout - auto_timeout, 0)
    if remaining <= 0:
        return False
    return wait_for_manual_cloudflare_v2(
        driver,
        timeout=remaining,
        poll_interval=5,
        return_to_url=return_to_url,
    )
