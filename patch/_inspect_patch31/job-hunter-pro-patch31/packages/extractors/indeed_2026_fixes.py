"""
Indeed Extractor 2026 Fixes (Patch 31).

Critical fixes from log analysis 2026-06-24:

BUG #1: URL Builder Duplicate attr(DSQF7)
  - easy_apply AND remote both pushed same code
  - Fix: Remote uses different filter mechanism (not attr code)

BUG #2: collect_job_cards Found N nodes, Collected 0
  - Indeed 2026 changed DOM structure
  - Old selector div.job_seen_beacon found cards but data-jk missing
  - Fix: Multi-strategy job_id extraction + new selectors + embedded JSON fallback

BUG #3: Cloudflare Turnstile Detection Missing
  - Indeed uses Cloudflare Bot Management now (not just hCaptcha)
  - Fix: Detect Turnstile + auto-click checkbox + wait for clearance

BUG #4: undetected-chromedriver Stealth Insufficient
  - Fix: Enhanced launch options + navigator overrides

Integration: Apply selective changes via INTEGRATION_SNIPPETS.md
"""
from __future__ import annotations
import os
import re
import time
import json
from typing import Optional
from urllib.parse import urlencode
from loguru import logger

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException,
)


# ============================================================
# SELECTORS UPDATE — Indeed 2026 DOM
# ============================================================
INDEED_SELECTORS_2026 = {
    # Job cards — multi-fallback for Indeed 2026 changes
    "job_card": (By.CSS_SELECTOR,
        "div[data-jk], "                              # Most reliable
        "td.resultContent, "                          # Mobile/legacy
        "li[data-jk], "                                # New 2026 layout
        "div[data-testid='slider_item'], "
        "div.job_seen_beacon, "                       # Legacy fallback
        "div.cardOutline"),                            # 2026 variant

    # Link inside card (job_id often here)
    "job_card_link": (By.CSS_SELECTOR,
        "a[data-jk], "
        "h2.jobTitle a, "
        "a.jcs-JobTitle, "
        "a[id^='job_']"),

    # Title — multi-fallback
    "job_card_title": (By.CSS_SELECTOR,
        "h2.jobTitle span[title], "
        "h2.jobTitle a span, "
        "h2.jobTitle, "
        "[data-testid='job-title'], "
        "span[title]"),

    # Company — multi-fallback
    "job_card_company": (By.CSS_SELECTOR,
        "[data-testid='company-name'], "
        "span.companyName, "
        "[data-testid*='company'], "
        "a[data-testid='company-link']"),

    # Location
    "job_card_location": (By.CSS_SELECTOR,
        "[data-testid='job-location'], "
        "[data-testid='text-location'], "
        "div.companyLocation"),

    # Cloudflare Turnstile (NEW)
    "cf_turnstile_iframe": (By.CSS_SELECTOR,
        "iframe[src*='challenges.cloudflare.com'], "
        "iframe[src*='turnstile'], "
        "iframe[title*='Cloudflare']"),

    "cf_turnstile_widget": (By.CSS_SELECTOR,
        ".cf-turnstile, "
        "[data-sitekey], "
        "#cf-turnstile-container"),

    "cf_challenge_text": (By.XPATH,
        "//*[contains(text(), 'Verify you are human') or "
        "contains(text(), 'Verifying you are human') or "
        "contains(text(), 'Just a moment') or "
        "contains(text(), 'Checking your browser')]"),
}


# ============================================================
# DATE_CODE Reference
# ============================================================
DATE_CODE = {
    "past_24h": "1",
    "past_3d": "3",
    "past_week": "7",
    "past_14d": "14",
    "past_month": "30",
    "any": "",
}


# ============================================================
# FIX #1: URL Builder
# ============================================================
def build_search_url_2026(base_url, query, filters):
    """
    Build Indeed search URL with proper 2026 parameters.
    
    Args:
        base_url: e.g. "https://www.indeed.com"
        query: search query string
        filters: SearchFilters object
    
    Returns: full URL string
    """
    params = {
        "q": query,
        "l": filters.location or "",
    }
    
    # Date filter
    date_posted = getattr(filters, "date_posted", "")
    if date_posted in DATE_CODE and DATE_CODE[date_posted]:
        params["fromage"] = DATE_CODE[date_posted]
    
    # Sort by date
    params["sort"] = "date"
    
    # FIX: Build sc filter — DO NOT duplicate attr()
    sc_parts = []
    if getattr(filters, "easy_apply_only", False):
        sc_parts.append("attr(DSQF7)")  # Indeed Apply only
    
    if sc_parts:
        params["sc"] = "0kf:" + "".join(sc_parts) + ";"
    
    # Remote: uses separate query parameter, NOT sc
    # Indeed handles "remote" via location field or radius
    if getattr(filters, "remote", False):
        # Append "remote" to query if not already there
        if "remote" not in query.lower():
            params["q"] = f"{query} remote"
    
    # Job type
    job_type = getattr(filters, "job_type", "")
    if job_type:
        type_map = {
            "Full-time": "fulltime",
            "Part-time": "parttime",
            "Contract": "contract",
            "Internship": "internship",
        }
        if job_type in type_map:
            params["jt"] = type_map[job_type]
    
    encoded = urlencode({k: v for k, v in params.items() if v})
    return f"{base_url}/jobs?{encoded}"


# ============================================================
# FIX #2: Enhanced collect_job_cards with multi-strategy
# ============================================================
def collect_job_cards_2026(driver, selectors=None, max_cards=50, scroll_count=8, sleep_func=None):
    """
    Multi-strategy job card collector for Indeed 2026.
    
    Returns list of card dicts with proper job_id extraction.
    """
    sels = selectors or INDEED_SELECTORS_2026
    cards = []
    seen = set()
    
    # Wait for content load
    time.sleep(2)
    
    # Lazy load scroll
    for _ in range(scroll_count):
        try:
            driver.execute_script("window.scrollBy(0, 800);")
            if sleep_func:
                sleep_func(1.0, 2.0)
            else:
                time.sleep(1.5)
        except Exception:
            pass
    
    # Find candidate nodes
    nodes = driver.find_elements(*sels["job_card"])
    logger.info(f"Found {len(nodes)} Indeed job card nodes (2026 selectors).")
    
    for idx, node in enumerate(nodes[:max_cards]):
        try:
            jid = _extract_job_id_multi_strategy(node, driver)
            
            if not jid:
                logger.debug(f"Card {idx}: no job_id (HTML: {node.get_attribute('outerHTML')[:200]})")
                continue
            
            if jid in seen:
                continue
            seen.add(jid)
            
            cards.append({
                "job_id": jid,
                "title": _safe_text(node, sels["job_card_title"]),
                "company": _safe_text(node, sels["job_card_company"]),
                "location": _safe_text(node, sels["job_card_location"]),
                "_element": node,
            })
        except StaleElementReferenceException:
            continue
        except Exception as e:
            logger.debug(f"Card {idx} error: {e}")
            continue
    
    # Fallback: parse embedded JSON if cards still empty
    if not cards and len(nodes) > 0:
        logger.info("Trying embedded JSON fallback...")
        json_cards = _parse_embedded_jobs_json(driver)
        if json_cards:
            logger.info(f"Recovered {len(json_cards)} cards from embedded JSON.")
            return json_cards[:max_cards]
    
    logger.info(f"Collected {len(cards)} unique Indeed cards.")
    return cards


def _extract_job_id_multi_strategy(node, driver=None):
    """
    Try multiple strategies to extract job_id from a card.
    Returns job_id string or None.
    """
    # Strategy 1: data-jk on element itself
    try:
        jid = node.get_attribute("data-jk")
        if jid:
            return jid
    except Exception:
        pass
    
    # Strategy 2: data-jk on link inside card
    try:
        link = node.find_element(By.CSS_SELECTOR, "a[data-jk]")
        jid = link.get_attribute("data-jk")
        if jid:
            return jid
    except NoSuchElementException:
        pass
    
    # Strategy 3: extract jk= from href
    try:
        for sel in ["h2 a", "a.jcs-JobTitle", "a[id^='job_']", "a"]:
            try:
                link = node.find_element(By.CSS_SELECTOR, sel)
                href = link.get_attribute("href") or ""
                if "jk=" in href:
                    m = re.search(r"jk=([a-f0-9]+)", href)
                    if m:
                        return m.group(1)
                if "/viewjob" in href:
                    m = re.search(r"/viewjob\?jk=([a-f0-9]+)", href)
                    if m:
                        return m.group(1)
            except NoSuchElementException:
                continue
    except Exception:
        pass
    
    # Strategy 4: id attribute pattern
    try:
        elem_id = node.get_attribute("id") or ""
        if elem_id.startswith("job_") or elem_id.startswith("mosaic-jobs-"):
            return elem_id.replace("job_", "").replace("mosaic-jobs-", "")
    except Exception:
        pass
    
    return None


def _safe_text(parent, selector):
    """Safe text extraction with fallback."""
    try:
        elem = parent.find_element(*selector)
        return elem.text.strip() or elem.get_attribute("title") or elem.get_attribute("aria-label") or ""
    except NoSuchElementException:
        return ""
    except Exception:
        return ""


def _parse_embedded_jobs_json(driver):
    """
    Fallback: parse Indeed embedded JSON in <script> tag.
    Indeed embeds job data as JSON object even when DOM rendering changes.
    """
    cards = []
    try:
        # Indeed typically embeds in window._initialData or window.mosaic.providerData
        script = """
        var data = null;
        try {
            if (window.mosaic && window.mosaic.providerData) {
                var k = Object.keys(window.mosaic.providerData)
                    .find(k => k.includes("jobs") || k.includes("results"));
                if (k) data = window.mosaic.providerData[k];
            }
            if (!data && window._initialData) data = window._initialData;
        } catch(e) {}
        return data ? JSON.stringify(data) : null;
        """
        raw = driver.execute_script(script)
        if not raw:
            return cards
        
        data = json.loads(raw)
        
        # Find jobs array (structure varies)
        jobs = _find_jobs_array(data)
        
        for job in jobs[:50]:
            jid = job.get("jobkey") or job.get("jk") or job.get("id")
            if not jid:
                continue
            cards.append({
                "job_id": jid,
                "title": job.get("title") or job.get("displayTitle") or "",
                "company": job.get("company") or job.get("companyName") or "",
                "location": job.get("formattedLocation") or job.get("location") or "",
                "_element": None,  # No DOM element; will re-find later
                "_from_json": True,
            })
    except Exception as e:
        logger.debug(f"JSON parse fallback failed: {e}")
    
    return cards


def _find_jobs_array(obj, depth=0, max_depth=5):
    """Recursively find array of jobs in nested JSON structure."""
    if depth > max_depth:
        return []
    
    if isinstance(obj, list):
        # Check if this looks like jobs array
        if len(obj) > 0 and isinstance(obj[0], dict):
            first_keys = set(obj[0].keys())
            if first_keys & {"jobkey", "jk", "title", "displayTitle"}:
                return obj
        return []
    
    if isinstance(obj, dict):
        # Check common keys
        for key in ["results", "metaData", "jobs", "items", "data"]:
            if key in obj:
                found = _find_jobs_array(obj[key], depth + 1, max_depth)
                if found:
                    return found
        
        # Recurse all values
        for value in obj.values():
            found = _find_jobs_array(value, depth + 1, max_depth)
            if found:
                return found
    
    return []


# ============================================================
# FIX #3: Cloudflare Turnstile Detection + Bypass
# ============================================================
def detect_cloudflare_challenge(driver) -> Optional[str]:
    """
    Detect if Cloudflare challenge is active.
    
    Returns:
        - "turnstile" if Turnstile widget detected
        - "interstitial" if generic CF check page
        - None if no challenge
    """
    try:
        page_lower = driver.page_source.lower()
        
        # Quick text checks
        cf_indicators = [
            "verify you are human",
            "verifying you are human",
            "just a moment",
            "checking your browser",
            "challenge-platform",
        ]
        
        has_text = any(ind in page_lower for ind in cf_indicators)
        
        # Check for Turnstile widget
        try:
            driver.find_element(*INDEED_SELECTORS_2026["cf_turnstile_iframe"])
            return "turnstile"
        except NoSuchElementException:
            pass
        
        try:
            driver.find_element(*INDEED_SELECTORS_2026["cf_turnstile_widget"])
            return "turnstile"
        except NoSuchElementException:
            pass
        
        if has_text:
            return "interstitial"
        
        return None
    except Exception as e:
        logger.debug(f"CF detection error: {e}")
        return None


def bypass_cloudflare_turnstile(driver, timeout=45) -> bool:
    """
    Attempt to bypass Cloudflare Turnstile challenge.
    
    Strategy:
    1. Wait for Turnstile widget to load
    2. Find checkbox iframe
    3. Switch to iframe context
    4. Click checkbox (human-like)
    5. Wait for clearance
    
    Returns True if bypass succeeded.
    """
    logger.info("🛡️  Attempting Cloudflare Turnstile bypass...")
    end = time.time() + timeout
    
    while time.time() < end:
        try:
            # Check if already cleared
            if detect_cloudflare_challenge(driver) is None:
                logger.success("✅ Cloudflare cleared")
                return True
            
            # Try finding and clicking checkbox in iframe
            try:
                iframes = driver.find_elements(
                    *INDEED_SELECTORS_2026["cf_turnstile_iframe"]
                )
                
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        
                        # Look for checkbox
                        for selector in [
                            "input[type='checkbox']",
                            "#challenge-stage",
                            "label.cb-lb",
                            "div[role='checkbox']",
                        ]:
                            try:
                                cb = driver.find_element(By.CSS_SELECTOR, selector)
                                if cb.is_displayed():
                                    # Human-like delay before click
                                    time.sleep(1.5)
                                    
                                    # Use ActionChains for natural movement
                                    try:
                                        ActionChains(driver).move_to_element(cb).pause(0.5).click().perform()
                                    except Exception:
                                        driver.execute_script("arguments[0].click();", cb)
                                    
                                    logger.info("🖱️  Turnstile checkbox clicked")
                                    driver.switch_to.default_content()
                                    time.sleep(5)
                                    break
                            except NoSuchElementException:
                                continue
                        
                        driver.switch_to.default_content()
                    except Exception:
                        driver.switch_to.default_content()
                        continue
            except NoSuchElementException:
                pass
            
            time.sleep(3)
        
        except Exception as e:
            logger.debug(f"Bypass attempt error: {e}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            time.sleep(2)
    
    logger.warning("⏰ Cloudflare bypass timeout — page may still be challenged")
    return False


def handle_cloudflare_if_present(driver, timeout=45) -> bool:
    """
    Convenience function: detect + bypass if needed.
    
    Returns True if no challenge OR successfully bypassed.
    """
    challenge = detect_cloudflare_challenge(driver)
    
    if challenge is None:
        return True  # No challenge, OK to proceed
    
    logger.warning(f"⚠️  Cloudflare {challenge} detected")
    
    if challenge == "turnstile":
        return bypass_cloudflare_turnstile(driver, timeout=timeout)
    
    elif challenge == "interstitial":
        # Just wait — interstitial usually auto-clears
        logger.info(f"⏸️  Waiting {timeout}s for interstitial to clear...")
        end = time.time() + timeout
        while time.time() < end:
            if detect_cloudflare_challenge(driver) is None:
                logger.success("✅ Interstitial cleared")
                return True
            time.sleep(3)
        
        logger.warning("⏰ Interstitial did not clear in time")
        return False
    
    return False


# ============================================================
# FIX #4: Enhanced Stealth Chrome Options
# ============================================================
def get_stealth_chrome_options():
    """
    Return ChromeOptions list with maximum stealth for Cloudflare.
    Use these with undetected_chromedriver.
    """
    return [
        # Anti-detection
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        
        # Performance
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        
        # Display (looks like real user)
        "--window-size=1920,1080",
        "--start-maximized",
        
        # Disable noise
        "--disable-notifications",
        "--disable-popup-blocking",
        "--disable-translate",
        
        # Cookies/storage
        "--enable-cookies",
    ]


def apply_stealth_javascript(driver):
    """
    Apply post-launch JS overrides to hide automation signals.
    Call after browser launch but before navigation.
    """
    stealth_js = """
    // Hide navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    
    // Spoof navigator.plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });
    
    // Spoof navigator.languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });
    
    // Override permission query
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": stealth_js
        })
        logger.debug("✅ Stealth JS overrides applied")
        return True
    except Exception as e:
        logger.debug(f"Stealth JS apply failed: {e}")
        return False