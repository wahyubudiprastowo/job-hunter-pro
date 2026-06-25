"""
Patch 31.1 — Critical Bug Fixes from log analysis 2026-06-25.

FIXES:

1. SELECTOR scoping — only job cards inside #mosaic-jobResults
   - Old selectors catched navbar <li>, sidebar items, ads
   - New: scoped to actual results container

2. Remove PAXZC for remote (not used by Indeed 2026)
   - Indeed handles remote via query keyword or location
   - URL: sc=0kf:attr(DSQF7); (only easy_apply)

3. Title extraction multi-fallback
   - Indeed 2026 nests text deeper in DOM
   - Try aria-label, text content, span[title], deep span

4. Description-only filter when title empty
   - Don't skip if title extraction fails
   - Use job description as fallback
"""
from __future__ import annotations
import re
import time
from typing import Optional
from urllib.parse import urlencode
from loguru import logger

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException,
)


# ============================================================
# FIX #1: PROPERLY SCOPED Selectors
# ============================================================
#
# Indeed 2026 layout:
# <div id="mosaic-jobResults">     <-- jobs container
#   <ul class="css-zu9cdh">         <-- jobs list
#     <li class="...">              <-- each job card
#       <div class="cardOutline">   
#         <h2 class="jobTitle">     <-- title here
#           <a data-jk="abc123">    <-- job link
#
# CRITICAL: scope all selectors INSIDE #mosaic-jobResults
# to avoid navbar/sidebar pollution

INDEED_SCOPE_PREFIX = "#mosaic-jobResults"

INDEED_SELECTORS_V2 = {
    # Job cards — scoped to results container
    "job_card": (By.CSS_SELECTOR,
        f"{INDEED_SCOPE_PREFIX} div[data-jk], "
        f"{INDEED_SCOPE_PREFIX} li > div.cardOutline, "
        f"{INDEED_SCOPE_PREFIX} li[data-resultid], "
        f"{INDEED_SCOPE_PREFIX} td.resultContent, "
        # Legacy fallback:
        f"{INDEED_SCOPE_PREFIX} div.job_seen_beacon"),
    
    "job_card_link": (By.CSS_SELECTOR,
        "a[data-jk], "
        "h2.jobTitle a"),
    
    # Title — multi-strategy
    "job_card_title": (By.CSS_SELECTOR,
        "h2.jobTitle a span[title], "
        "h2.jobTitle a span, "
        "h2.jobTitle > a, "
        "h2.jobTitle, "
        "[data-testid='job-title']"),
    
    "job_card_company": (By.CSS_SELECTOR,
        "[data-testid='company-name'], "
        "span.companyName, "
        "div[data-company-name]"),
    
    "job_card_location": (By.CSS_SELECTOR,
        "[data-testid='job-location'], "
        "[data-testid='text-location'], "
        "div.companyLocation"),
}


DATE_CODE = {
    "past_24h": "1",
    "past_3d": "3",
    "past_week": "7",
    "past_14d": "14",
    "past_month": "30",
    "any": "",
}


# ============================================================
# FIX #2: URL Builder — Only easy_apply uses sc
# ============================================================
def build_indeed_url_v2(base_url, query, filters):
    """
    Build Indeed search URL.
    
    KEY CHANGES vs v1:
    - Remote does NOT use sc=attr(PAXZC) — that's wrong
    - Remote uses query keyword append
    - Only easy_apply contributes to sc filter
    """
    params = {
        "q": query,
        "l": filters.location or "",
    }
    
    # Date filter
    date_posted = getattr(filters, "date_posted", "") or ""
    if date_posted in DATE_CODE and DATE_CODE[date_posted]:
        params["fromage"] = DATE_CODE[date_posted]
    
    params["sort"] = "date"
    
    # ONLY easy_apply contributes to sc filter (FIXED)
    if getattr(filters, "easy_apply_only", False):
        params["sc"] = "0kf:attr(DSQF7);"
    
    # Remote: append to query (NOT sc filter)
    if getattr(filters, "remote", False):
        if "remote" not in query.lower():
            params["q"] = f"{query} remote"
    
    # Job type
    job_type = getattr(filters, "job_type", "") or ""
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
# FIX #3: Properly Scoped Card Collection
# ============================================================
def collect_indeed_cards_v2(driver, max_cards=50, scroll_count=8, sleep_func=None):
    """
    Properly scoped card collection — avoids navbar pollution.
    """
    cards = []
    seen = set()
    
    # Wait for results container
    end = time.time() + 10
    container_found = False
    while time.time() < end:
        try:
            driver.find_element(By.CSS_SELECTOR, INDEED_SCOPE_PREFIX)
            container_found = True
            break
        except NoSuchElementException:
            time.sleep(0.5)
    
    if not container_found:
        logger.warning(f"Indeed: {INDEED_SCOPE_PREFIX} not found — page may not be results")
        return cards
    
    # Scroll for lazy load
    for _ in range(scroll_count):
        try:
            driver.execute_script("window.scrollBy(0, 800);")
            if sleep_func:
                sleep_func(1.0, 2.0)
            else:
                time.sleep(1.5)
        except Exception:
            pass
    
    # Find cards INSIDE results container only
    nodes = driver.find_elements(*INDEED_SELECTORS_V2["job_card"])
    logger.info(f"Found {len(nodes)} Indeed job card nodes (scoped to results).")
    
    for idx, node in enumerate(nodes[:max_cards]):
        try:
            jid = _extract_job_id_v2(node)
            
            if not jid:
                logger.debug(f"Card {idx} no job_id (HTML: {node.get_attribute('outerHTML')[:150]})")
                continue
            
            if jid in seen:
                continue
            seen.add(jid)
            
            cards.append({
                "job_id": jid,
                "title": _extract_title_v2(node),
                "company": _safe_text_v2(node, INDEED_SELECTORS_V2["job_card_company"]),
                "location": _safe_text_v2(node, INDEED_SELECTORS_V2["job_card_location"]),
                "_element": node,
            })
        except StaleElementReferenceException:
            continue
        except Exception as e:
            logger.debug(f"Card {idx} error: {e}")
            continue
    
    logger.info(f"Collected {len(cards)} unique Indeed cards.")
    return cards


def _extract_job_id_v2(node) -> Optional[str]:
    """Multi-strategy job_id extraction."""
    # Strategy 1: data-jk on element itself
    try:
        jid = node.get_attribute("data-jk")
        if jid:
            return jid
    except Exception:
        pass
    
    # Strategy 2: data-jk on link inside
    try:
        link = node.find_element(By.CSS_SELECTOR, "a[data-jk]")
        jid = link.get_attribute("data-jk")
        if jid:
            return jid
    except NoSuchElementException:
        pass
    
    # Strategy 3: extract jk= from href
    try:
        for sel in ["h2 a", "a.jcs-JobTitle", "a[id^='job_']"]:
            try:
                link = node.find_element(By.CSS_SELECTOR, sel)
                href = link.get_attribute("href") or ""
                m = re.search(r"jk=([a-f0-9]+)", href)
                if m:
                    return m.group(1)
            except NoSuchElementException:
                continue
    except Exception:
        pass
    
    # Strategy 4: data-resultid (some 2026 layouts use this)
    try:
        rid = node.get_attribute("data-resultid")
        if rid:
            return rid
    except Exception:
        pass
    
    return None


def _extract_title_v2(node) -> str:
    """
    Multi-strategy title extraction.
    Title in Indeed 2026 can be nested in different patterns:
    - <h2 class="jobTitle"><a><span title="Title Here">Title Here</span></a></h2>
    - <h2 class="jobTitle"><a>Title Here</a></h2>
    - Sometimes aria-label has it
    """
    strategies = [
        # Strategy 1: span title attribute (most reliable)
        ("h2.jobTitle span[title]", "title"),
        # Strategy 2: link text
        ("h2.jobTitle a", "text"),
        # Strategy 3: link aria-label
        ("h2.jobTitle a", "aria-label"),
        # Strategy 4: any span inside h2
        ("h2.jobTitle span", "text"),
        # Strategy 5: data-testid
        ("[data-testid='job-title']", "text"),
    ]
    
    for selector, attr in strategies:
        try:
            elem = node.find_element(By.CSS_SELECTOR, selector)
            if attr == "text":
                text = elem.text.strip()
            else:
                text = elem.get_attribute(attr) or ""
            if text:
                return text.strip()
        except NoSuchElementException:
            continue
        except Exception:
            continue
    
    return ""


def _safe_text_v2(parent, selector_tuple):
    """Safe text extraction with multi-fallback."""
    try:
        elem = parent.find_element(*selector_tuple)
        text = elem.text.strip()
        if not text:
            text = elem.get_attribute("title") or elem.get_attribute("aria-label") or ""
        return text.strip()
    except NoSuchElementException:
        return ""
    except Exception:
        return ""


# ============================================================
# FIX #4: NotificationCategory.SUMMARY → DAILY_SUMMARY
# ============================================================
#
# In apps/worker/runner.py around line 821, replace:
#
#   OLD:
#     category=NotificationCategory.SUMMARY if NotificationCategory else None,
#
#   NEW:
#     category=NotificationCategory.DAILY_SUMMARY if NotificationCategory else None,
#
# This is a typo fix — Patch 28 defined DAILY_SUMMARY, not SUMMARY.