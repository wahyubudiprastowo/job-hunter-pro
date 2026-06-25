"""
Patch 31.1 — Critical Indeed fixes from log analysis.

Focused fixes:
- scope selectors to job results container
- remove invalid remote sc filter usage
- stronger title extraction
"""
from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import urlencode

from loguru import logger
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By


INDEED_SCOPE_PREFIX = "#mosaic-jobResults"

INDEED_SELECTORS_V2 = {
    "job_card": (
        By.CSS_SELECTOR,
        f"{INDEED_SCOPE_PREFIX} div[data-jk], "
        f"{INDEED_SCOPE_PREFIX} li > div.cardOutline, "
        f"{INDEED_SCOPE_PREFIX} li[data-resultid], "
        f"{INDEED_SCOPE_PREFIX} td.resultContent, "
        f"{INDEED_SCOPE_PREFIX} div.job_seen_beacon",
    ),
    "job_card_link": (
        By.CSS_SELECTOR,
        "a[data-jk], h2.jobTitle a",
    ),
    "job_card_title": (
        By.CSS_SELECTOR,
        "h2.jobTitle a span[title], h2.jobTitle a span, h2.jobTitle > a, "
        "h2.jobTitle, [data-testid='job-title']",
    ),
    "job_card_company": (
        By.CSS_SELECTOR,
        "[data-testid='company-name'], span.companyName, div[data-company-name]",
    ),
    "job_card_location": (
        By.CSS_SELECTOR,
        "[data-testid='job-location'], [data-testid='text-location'], div.companyLocation",
    ),
}


DATE_CODE = {
    "past_24h": "1",
    "past_3d": "3",
    "past_week": "7",
    "past_14d": "14",
    "past_month": "30",
    "any": "",
}


def build_indeed_url_v2(base_url, query, filters):
    params = {
        "q": query,
        "l": filters.location or "",
    }

    date_posted = getattr(filters, "date_posted", "") or ""
    if date_posted in DATE_CODE and DATE_CODE[date_posted]:
        params["fromage"] = DATE_CODE[date_posted]

    params["sort"] = "date"

    if getattr(filters, "easy_apply_only", False):
        params["sc"] = "0kf:attr(DSQF7);"

    if getattr(filters, "remote", False) and "remote" not in query.lower():
        params["q"] = f"{query} remote"

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


def collect_indeed_cards_v2(driver, max_cards=50, scroll_count=8, sleep_func=None, base_url="https://www.indeed.com"):
    cards = []
    seen = set()

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
        logger.warning(f"Indeed: {INDEED_SCOPE_PREFIX} not found - page may not be results")
        return cards

    for _ in range(scroll_count):
        try:
            driver.execute_script("window.scrollBy(0, 800);")
            if sleep_func:
                sleep_func(1.0, 2.0)
            else:
                time.sleep(1.5)
        except Exception:
            pass

    nodes = driver.find_elements(*INDEED_SELECTORS_V2["job_card"])
    logger.info(f"Found {len(nodes)} Indeed job card nodes (scoped to results).")

    for idx, node in enumerate(nodes[:max_cards]):
        try:
            jid = _extract_job_id_v2(node)
            if not jid:
                html = (node.get_attribute("outerHTML") or "")[:150].replace("\n", " ")
                logger.debug(f"Card {idx} no job_id (HTML: {html})")
                continue
            if jid in seen:
                continue
            title = _extract_title_v2(node)
            company = _safe_text_v2(node, INDEED_SELECTORS_V2["job_card_company"])
            location = _safe_text_v2(node, INDEED_SELECTORS_V2["job_card_location"])
            url = _extract_card_url_v2(node, jid, base_url)

            # Guard against non-job or broken nodes that produce no meaningful metadata.
            if not title and not company and not location:
                html = (node.get_attribute("outerHTML") or "")[:180].replace("\n", " ")
                logger.debug(f"Card {idx} ignored: empty title/company/location (HTML: {html})")
                continue

            seen.add(jid)
            cards.append({
                "job_id": jid,
                "title": title,
                "company": company,
                "location": location,
                "url": url,
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
    try:
        jid = node.get_attribute("data-jk")
        if jid:
            return jid
    except Exception:
        pass

    try:
        link = node.find_element(By.CSS_SELECTOR, "a[data-jk]")
        jid = link.get_attribute("data-jk")
        if jid:
            return jid
    except NoSuchElementException:
        pass

    try:
        for sel in ["h2 a", "a.jcs-JobTitle", "a[id^='job_']"]:
            try:
                link = node.find_element(By.CSS_SELECTOR, sel)
            except NoSuchElementException:
                continue
            href = link.get_attribute("href") or ""
            match = re.search(r"jk=([A-Za-z0-9_-]+)", href)
            if match:
                return match.group(1)
    except Exception:
        pass

    try:
        rid = node.get_attribute("data-resultid")
        if rid:
            return rid
    except Exception:
        pass
    return None


def _extract_title_v2(node) -> str:
    strategies = [
        ("h2.jobTitle span[title]", "title"),
        ("h2.jobTitle a", "aria-label"),
        ("h2.jobTitle a", "text"),
        ("h2.jobTitle span", "text"),
        ("h2.jobTitle", "text"),
        ("[data-testid='job-title']", "text"),
        ("a[data-jk]", "text"),
        ("[role='group'][aria-label]", "aria-label"),
    ]
    for selector, attr in strategies:
        try:
            elem = node.find_element(By.CSS_SELECTOR, selector)
            if attr == "text":
                text = elem.text.strip()
            else:
                text = elem.get_attribute(attr) or ""
            if text and len(text.strip()) > 3:
                return text.strip()
        except Exception:
            continue
    return ""


def _extract_card_url_v2(node, jid: str, base_url: str) -> str:
    for selector in ("a[data-jk]", "h2.jobTitle a", "a[id^='job_']", "a[href*='jk=']"):
        try:
            link = node.find_element(By.CSS_SELECTOR, selector)
            href = (link.get_attribute("href") or "").strip()
            if href and "jk=" in href:
                return href
        except Exception:
            continue
    return f"{base_url}/viewjob?jk={jid}"


def _safe_text_v2(parent, selector_tuple):
    try:
        elem = parent.find_element(*selector_tuple)
        text = elem.text.strip()
        if not text:
            text = elem.get_attribute("title") or elem.get_attribute("aria-label") or ""
        return text.strip()
    except Exception:
        return ""
