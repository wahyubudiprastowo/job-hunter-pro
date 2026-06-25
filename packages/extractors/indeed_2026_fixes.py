"""
Indeed Extractor 2026 Fixes (Patch 31).

Additive helper for Indeed-specific DOM, Cloudflare, and search URL changes.
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional
from urllib.parse import urlencode

from loguru import logger
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


INDEED_SELECTORS_2026 = {
    "job_card": (
        By.CSS_SELECTOR,
        "div[data-jk], td.resultContent, li[data-jk], "
        "div[data-testid='slider_item'], div.job_seen_beacon, div.cardOutline",
    ),
    "job_card_link": (
        By.CSS_SELECTOR,
        "a[data-jk], h2.jobTitle a, a.jcs-JobTitle, a[id^='job_']",
    ),
    "job_card_title": (
        By.CSS_SELECTOR,
        "h2.jobTitle span[title], h2.jobTitle a span, h2.jobTitle, "
        "[data-testid='job-title'], span[title]",
    ),
    "job_card_company": (
        By.CSS_SELECTOR,
        "[data-testid='company-name'], span.companyName, "
        "[data-testid*='company'], a[data-testid='company-link']",
    ),
    "job_card_location": (
        By.CSS_SELECTOR,
        "[data-testid='job-location'], [data-testid='text-location'], div.companyLocation",
    ),
    "cf_turnstile_iframe": (
        By.CSS_SELECTOR,
        "iframe[src*='challenges.cloudflare.com'], "
        "iframe[src*='turnstile'], iframe[title*='Cloudflare']",
    ),
    "cf_turnstile_widget": (
        By.CSS_SELECTOR,
        ".cf-turnstile, [data-sitekey], #cf-turnstile-container",
    ),
    "cf_checkbox_direct": (
        By.CSS_SELECTOR,
        "input[type='checkbox'], div[role='checkbox'], label.cb-lb, #challenge-stage",
    ),
    "cf_return_home": (
        By.XPATH,
        "//a[contains(., 'Return home')] | //button[contains(., 'Return home')]",
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


def build_search_url_2026(base_url, query, filters):
    params = {
        "q": query,
        "l": filters.location or "",
    }

    date_posted = getattr(filters, "date_posted", "")
    if date_posted in DATE_CODE and DATE_CODE[date_posted]:
        params["fromage"] = DATE_CODE[date_posted]

    params["sort"] = "date"

    sc_parts = []
    if getattr(filters, "easy_apply_only", False):
        sc_parts.append("attr(DSQF7)")
    if sc_parts:
        params["sc"] = "0kf:" + "".join(sc_parts) + ";"

    if getattr(filters, "remote", False) and "remote" not in query.lower():
        params["q"] = f"{query} remote"

    job_type = getattr(filters, "job_type", "")
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


def collect_job_cards_2026(driver, selectors=None, max_cards=50, scroll_count=8, sleep_func=None):
    sels = selectors or INDEED_SELECTORS_2026
    cards = []
    seen = set()

    time.sleep(2)

    for _ in range(scroll_count):
        try:
            driver.execute_script("window.scrollBy(0, 800);")
            if sleep_func:
                sleep_func(1.0, 2.0)
            else:
                time.sleep(1.5)
        except Exception:
            pass

    nodes = driver.find_elements(*sels["job_card"])
    logger.info(f"Found {len(nodes)} Indeed job card nodes (2026 selectors).")

    for idx, node in enumerate(nodes[:max_cards]):
        try:
            jid = _extract_job_id_multi_strategy(node)
            if not jid:
                html = (node.get_attribute("outerHTML") or "")[:200].replace("\n", " ")
                logger.debug(f"Card {idx}: no job_id (HTML: {html})")
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

    if not cards and len(nodes) > 0:
        logger.info("Trying embedded JSON fallback...")
        json_cards = _parse_embedded_jobs_json(driver)
        if json_cards:
            logger.info(f"Recovered {len(json_cards)} cards from embedded JSON.")
            return json_cards[:max_cards]

    logger.info(f"Collected {len(cards)} unique Indeed cards.")
    return cards


def _extract_job_id_multi_strategy(node):
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
        for sel in ["h2 a", "a.jcs-JobTitle", "a[id^='job_']", "a"]:
            try:
                link = node.find_element(By.CSS_SELECTOR, sel)
            except NoSuchElementException:
                continue
            href = link.get_attribute("href") or ""
            if "jk=" in href:
                match = re.search(r"jk=([A-Za-z0-9_-]+)", href)
                if match:
                    return match.group(1)
    except Exception:
        pass

    try:
        elem_id = node.get_attribute("id") or ""
        if elem_id.startswith("job_") or elem_id.startswith("mosaic-jobs-"):
            return elem_id.replace("job_", "").replace("mosaic-jobs-", "")
    except Exception:
        pass

    return None


def _safe_text(parent, selector):
    try:
        elem = parent.find_element(*selector)
        return elem.text.strip() or elem.get_attribute("title") or elem.get_attribute("aria-label") or ""
    except Exception:
        return ""


def _parse_embedded_jobs_json(driver):
    cards = []
    try:
        raw = driver.execute_script(
            """
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
        )
        if not raw:
            return cards
        data = json.loads(raw)
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
                "_element": None,
                "_from_json": True,
            })
    except Exception as e:
        logger.debug(f"JSON parse fallback failed: {e}")
    return cards


def _find_jobs_array(obj, depth=0, max_depth=5):
    if depth > max_depth:
        return []
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict):
            first_keys = set(obj[0].keys())
            if first_keys & {"jobkey", "jk", "title", "displayTitle"}:
                return obj
        return []
    if isinstance(obj, dict):
        for key in ["results", "metaData", "jobs", "items", "data"]:
            if key in obj:
                found = _find_jobs_array(obj[key], depth + 1, max_depth)
                if found:
                    return found
        for value in obj.values():
            found = _find_jobs_array(value, depth + 1, max_depth)
            if found:
                return found
    return []


def detect_cloudflare_challenge(driver) -> Optional[str]:
    try:
        page_lower = driver.page_source.lower()
        indicators = [
            "verify you are human",
            "verifying you are human",
            "just a moment",
            "checking your browser",
            "challenge-platform",
            "additional verification required",
            "return home",
        ]
        has_text = any(ind in page_lower for ind in indicators)

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
        try:
            checkbox = driver.find_element(*INDEED_SELECTORS_2026["cf_checkbox_direct"])
            if checkbox.is_displayed():
                return "turnstile"
        except Exception:
            pass
        if has_text:
            return "interstitial"
        return None
    except Exception as e:
        logger.debug(f"CF detection error: {e}")
        return None


def bypass_cloudflare_turnstile(driver, timeout=45) -> bool:
    logger.info("Attempting Cloudflare Turnstile bypass...")
    end = time.time() + timeout
    while time.time() < end:
        try:
            if detect_cloudflare_challenge(driver) is None:
                logger.success("Cloudflare cleared")
                return True

            for selector in [
                "input[type='checkbox']",
                "#challenge-stage",
                "label.cb-lb",
                "div[role='checkbox']",
            ]:
                try:
                    cb = driver.find_element(By.CSS_SELECTOR, selector)
                except NoSuchElementException:
                    continue
                if cb.is_displayed():
                    time.sleep(1.5)
                    try:
                        ActionChains(driver).move_to_element(cb).pause(0.5).click().perform()
                    except Exception:
                        driver.execute_script("arguments[0].click();", cb)
                    logger.info("Direct Cloudflare checkbox clicked")
                    time.sleep(5)
                    if detect_cloudflare_challenge(driver) is None:
                        logger.success("Cloudflare cleared")
                        return True

            iframes = driver.find_elements(*INDEED_SELECTORS_2026["cf_turnstile_iframe"])
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    for selector in [
                        "input[type='checkbox']",
                        "#challenge-stage",
                        "label.cb-lb",
                        "div[role='checkbox']",
                    ]:
                        try:
                            cb = driver.find_element(By.CSS_SELECTOR, selector)
                        except NoSuchElementException:
                            continue
                        if cb.is_displayed():
                            time.sleep(1.5)
                            try:
                                ActionChains(driver).move_to_element(cb).pause(0.5).click().perform()
                            except Exception:
                                driver.execute_script("arguments[0].click();", cb)
                            logger.info("Turnstile checkbox clicked")
                            driver.switch_to.default_content()
                            time.sleep(5)
                            break
                    driver.switch_to.default_content()
                except Exception:
                    driver.switch_to.default_content()
                    continue
            time.sleep(3)
        except Exception as e:
            logger.debug(f"Bypass attempt error: {e}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            time.sleep(2)
    logger.warning("Cloudflare bypass timeout")
    return False


def _restore_post_challenge_url(driver, return_to_url: str | None) -> None:
    if not return_to_url:
        return
    try:
        current = (driver.current_url or "").rstrip("/").lower()
    except Exception:
        current = ""
    home_urls = {
        "https://www.indeed.com",
        "https://www.indeed.com/",
        "https://indeed.com",
        "https://indeed.com/",
    }
    if current in {u.rstrip("/").lower() for u in home_urls}:
        logger.info(f"Cloudflare cleared - restoring target URL: {return_to_url}")
        driver.get(return_to_url)
        time.sleep(3)


def wait_for_manual_cloudflare_clearance(driver, timeout=120, return_to_url: str | None = None) -> bool:
    logger.warning(
        "Cloudflare requires manual verification in the browser. "
        "Complete the checkbox/challenge and wait for bot to continue."
    )
    end = time.time() + timeout
    while time.time() < end:
        if detect_cloudflare_challenge(driver) is None:
            logger.success("Manual Cloudflare verification cleared")
            _restore_post_challenge_url(driver, return_to_url)
            return True
        time.sleep(2)
    logger.warning("Manual Cloudflare verification timeout")
    return False


def handle_cloudflare_if_present(driver, timeout=45, return_to_url: str | None = None) -> bool:
    challenge = detect_cloudflare_challenge(driver)
    if challenge is None:
        return True
    logger.warning(f"Cloudflare {challenge} detected")
    if challenge == "turnstile":
        auto_timeout = min(timeout, 20)
        if bypass_cloudflare_turnstile(driver, timeout=auto_timeout):
            _restore_post_challenge_url(driver, return_to_url)
            return True
        remaining = max(timeout - auto_timeout, 0)
        if remaining:
            return wait_for_manual_cloudflare_clearance(
                driver,
                timeout=remaining,
                return_to_url=return_to_url,
            )
        return False
    if challenge == "interstitial":
        logger.info("Cloudflare interstitial requires manual completion or direct checkbox clear.")
        if wait_for_manual_cloudflare_clearance(
            driver,
            timeout=timeout,
            return_to_url=return_to_url,
        ):
            return True
        logger.warning("Interstitial did not clear in time")
        return False
    return False


def get_stealth_chrome_options():
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--start-maximized",
        "--disable-notifications",
        "--disable-popup-blocking",
        "--disable-translate",
        "--enable-cookies",
    ]


def apply_stealth_javascript(driver):
    stealth_js = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js})
        logger.debug("Stealth JS overrides applied")
        return True
    except Exception as e:
        logger.debug(f"Stealth JS apply failed: {e}")
        return False
